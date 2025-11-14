#!/usr/bin/env python3
"""
Seed SSM Parameter Store from local YAML config files.

This script follows this procedure to publish configuration parameters:
- Step 1: Discover YAML files in config/<function>/<env>.yaml
- Step 2: Load and validate each YAML document
- Step 3: Extract only the `params:` section (ignore `secrets:`)
- Step 4: Flatten nested keys into SSM paths
- Step 5: Upsert parameters into AWS Systems Manager Parameter Store

CLI usage:
    $ python seed_ssm_params.py --app-name cloudshortener --root config --env-allow dev prod
    $ python seed_ssm_params.py --app-name cloudshortener --dry-run
    $ python seed_ssm_params.py --app-name cloudshortener --tags "Owner=Pesho,Service=cloudshortener"
    $ python seed_ssm_params.py --app-name cloudshortener --aws-profile my-profile

AWS credentials/region:
    - Use --aws-profile to select a profile from ~/.aws/{credentials,config}.
    - If omitted, boto3’s default resolution applies (env vars, default profile, etc).

Behavior:
    - Writes parameters under: /<app>/<env>/<function>/<...>
      Example: /cloudshortener/dev/shorten_url/redis/host = "redis.example"
    - Values are stored as String (4 KB limit). Use Secrets Manager for credentials.
    - Uses overwrite semantics (idempotent updates).
    - Adds optional tags and a default set of tags: App, Env, Function.

Raises:
    FileNotFoundError: If the --root directory does not exist.
    ValueError: For malformed --tags input or unexpected YAML structure.
    botocore.exceptions.BotoCoreError / ClientError: For AWS API failures.
"""

import argparse
import json
import pathlib
from typing import Any, Dict, Iterable

import boto3
import yaml


# TODO: add support for Advanced parameters or chunking for larger payloads if needed
# TODO: support per-key SecureString opt-in via an allowlist (kept as params, not secrets)
# TODO: add structured logging and retry/backoff on throttling


def _load_yaml(path: pathlib.Path) -> Dict[str, Any]:
    """Load a YAML file into a Python dict.

    Args:
        path (Path): Path to a YAML file.

    Returns:
        Dict[str, Any]: Parsed YAML document (empty dict if file is empty).
    """
    with path.open("r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    return data or {}


def _flatten(prefix: str, data: Dict[str, Any]) -> Dict[str, str]:
    """Flatten nested dictionaries into SSM path -> string value.

    Rules:
        - Nested dicts are converted into path segments: prefix/key/subkey
        - Non-dict values are stringified
        - None becomes empty string

    Args:
        prefix (str): The SSM path prefix (e.g., "/cloudshortener/dev/shorten_url").
        data (Dict[str, Any]): Nested dictionary to flatten.

    Returns:
        Dict[str, str]: Mapping of full SSM path => string value.

    Example:
        >>> _flatten("/app/dev/svc", {"redis": {"host": "h", "port": 6379}})
        {'/app/dev/svc/redis/host': 'h', '/app/dev/svc/redis/port': '6379'}
    """
    out: Dict[str, str] = {}

    def _walk(base: str, node: Any) -> None:
        if isinstance(node, dict):
            for k, v in node.items():
                _walk(f"{base}/{k}", v)
        else:
            out[base] = "" if node is None else str(node)

    _walk(prefix, data)
    return out


def _yaml_config_files(root: pathlib.Path) -> Iterable[pathlib.Path]:
    """Yield config YAML files under the given root (config/<function>/*.yaml)."""
    for function_dir in sorted(p for p in root.iterdir() if p.is_dir()):
        yield from sorted(function_dir.glob("*.yaml"))


def _normalize_user_tags(tag_str: str) -> list[dict[str, str]]:
    """Normalize a comma-separated tag string into AWS tag dicts.

    Input format:
        "Key1=Val1,Key2=Val2"

    Returns:
        List[Dict[str, str]] suitable for AWS tagging APIs.

    Raises:
        ValueError: if any tag entry is malformed (missing '=' or empty key).
    """
    tags: list[dict[str, str]] = []
    if not tag_str:
        return tags

    for raw in tag_str.split(","):
        item = raw.strip()
        if not item:
            # Skip empty segments like trailing commas, but do not error.
            continue
        if "=" not in item:
            raise ValueError(f"Malformed tag (expected key=value): '{item}'")
        key, value = item.split("=", 1)
        key = key.strip()
        value = value.strip()
        if not key:
            raise ValueError(f"Malformed tag (empty key): '{item}'")
        tags.append({"Key": key, "Value": value})
    return tags


def _put_parameter(
    ssm_client,
    name: str,
    value: str,
    tags: list[dict[str, str]] | None = None,
    dry_run: bool = False,
) -> None:
    """Create or update a String parameter with overwrite semantics.

    Args:
        ssm_client: boto3 SSM client.
        name (str): Full parameter path.
        value (str): Parameter value (<= 4 KB).
        tags (list[dict[str,str]] | None): Optional tags to attach on create.
        dry_run (bool): If True, print the action and skip the API call.
    """
    msg = f"SSM put-parameter {json.dumps({'Name': name, 'Type': 'String', 'Value': value})}"
    if dry_run:
        print("[DRY-RUN]", msg)
        return

    # Check if the SSM parameter exists:
    # - if exists: update the parameter via overwrite
    # - if not exists: create the parameter with tags
    exists = False
    try:
        ssm_client.get_parameter(Name=name)
        exists = True
    except ssm_client.exceptions.ParameterNotFound:
        pass

    kwargs = {
        "Name": name,
        "Type": "String",
        "Value": value,
    }
    if exists:
        # Existing parameter → overwrite (no tags)
        kwargs["Overwrite"] = True
        ssm_client.put_parameter(**kwargs)
    else:
        # New parameter → can attach tags
        if tags:
            kwargs["Tags"] = tags
        ssm_client.put_parameter(**kwargs)
    print(msg)


def main(argv: list[str] | None = None) -> None:
    """CLI entry point.

    Steps:
        - Parse CLI arguments
        - Discover config YAMLs under --root
        - For each file, extract `params:` and compute SSM paths
        - Write (or preview) parameters with idempotent upserts

    Raises:
        FileNotFoundError: when --root is not a directory.
        ValueError: when --tags is malformed or YAML contents are invalid.
        boto3/botocore exceptions: on AWS API failures.
    """
    parser = argparse.ArgumentParser(
        prog="seed_ssm_params.py",
        description="Publish configuration parameters from config/<function>/<env>.yaml to AWS SSM Parameter Store",
    )
    parser.add_argument(
        "--app-name",
        required=True,
        help="Application name for the SSM path prefix (e.g., cloudshortener)",
    )
    parser.add_argument(
        "--root",
        default="config",
        help="Root directory containing <function>/<env>.yaml files (default: config)",
    )
    parser.add_argument(
        "--env-allow",
        nargs="*",
        default=None,
        help="Optional environment allowlist (e.g., dev staging prod). If omitted, all envs found are processed.",
    )
    parser.add_argument(
        "--tags",
        default="",
        help='Comma-separated tags to attach on create, e.g. "Owner=Pesho,Service=cloudshortener"',
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview actions without writing to AWS",
    )
    parser.add_argument(
        "--aws-profile",
        default=None,
        help="AWS shared config/credentials profile name to use (e.g., default, dev, prod)",
    )

    args = parser.parse_args(argv)

    # Access hyphenated argument name safely (argparse maps to underscore attribute)
    app_name = getattr(args, "app_name", None)
    if not app_name:
        raise ValueError("Missing required --app-name")

    root = pathlib.Path(args.root)
    if not root.is_dir():
        raise FileNotFoundError(f"Bad config root: {root}")

    extra_tags = _normalize_user_tags(args.tags)

    # Create a session that honors the selected AWS profile (credentials + region)
    if args.aws_profile:
        session = boto3.Session(profile_name=args.aws_profile)
    else:
        session = boto3.Session()

    ssm = session.client("ssm")

    writes = 0
    for yaml_path in _yaml_config_files(root):
        # Derive <function> and <env> from path
        function_name = yaml_path.parent.name          # e.g., "shorten_url"
        env_name = yaml_path.stem                      # e.g., "dev"

        if args.env_allow and env_name not in args.env_allow:
            continue

        doc = _load_yaml(yaml_path)
        params = doc.get("params") or {}
        if not isinstance(params, dict):
            raise ValueError(f"'params' section must be a mapping in {yaml_path}")
        if not params:
            # nothing to publish in this file; continue silently
            continue

        prefix = f"/{app_name}/{env_name}/{function_name}"
        flat = _flatten(prefix, params)

        # Compose tags once per file; App/Env/Function are consistent for all keys in this YAML
        base_tags = [
            {"Key": "App", "Value": app_name},
            {"Key": "Env", "Value": env_name},
            {"Key": "Function", "Value": function_name},
        ] + extra_tags

        for name, value in sorted(flat.items()):
            _put_parameter(ssm, name=name, value=value, tags=base_tags, dry_run=args.dry_run)
            writes += 1

    print(f"Done. {'Previewed' if args.dry_run else 'Wrote'} {writes} parameters.")


if __name__ == "__main__":
    # Let exceptions raise naturally; a traceback signals non-zero exit to the shell.
    main()
