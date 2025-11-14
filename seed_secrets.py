#!/usr/bin/env python3
"""
Seed AWS Secrets Manager from local YAML config files.

This script follows this procedure to publish application secrets:
- Step 1: Discover YAML files in config/<function>/<env>.yaml
- Step 2: Load and validate each YAML document
- Step 3: Extract only the `secrets:` section (ignore `params:`)
- Step 4: Group secrets by top-level component (e.g., "redis")
- Step 5: Create or update one Secrets Manager secret per component

CLI usage:
    $ python seed_secrets.py --app-name cloudshortener --root config --env-allow dev prod
    $ python seed_secrets.py --app-name cloudshortener --dry-run
    $ python seed_secrets.py --app-name cloudshortener --tags "Owner=Pesho,Service=cloudshortener"
    $ python seed_secrets.py --app-name cloudshortener --aws-profile my-profile
    $ python seed_secrets.py --app-name cloudshortener --kms-key-id alias/aws/secretsmanager

AWS credentials/region:
    - Use --aws-profile to select a profile from ~/.aws/{credentials,config}.
    - If omitted, boto3’s default resolution applies (env vars, default profile, etc).

Behavior:
    - Creates one secret per component under name:
        <AppName>/<env>/<function>/<component>
      Example:
        cloudshortener/dev/shorten_url/redis
      Payload (SecretString) is the component dict as JSON, e.g.:
        {"username": "...", "password": "..."}
    - Never prints secret values to stdout.
    - Create vs update:
        * If secret does not exist → create with tags (+ optional KMS key).
        * If secret exists → update value (PutSecretValue) and apply tags (TagResource).
    - Adds optional user tags plus a default set: App, Env, Function, Component.

Raises:
    FileNotFoundError: If the --root directory does not exist.
    ValueError: For malformed --tags input or unexpected YAML structure.
    botocore.exceptions.BotoCoreError / ClientError: For AWS API failures.

Example:
    >>> # dry-run to preview secret names and keys (no writes)
    >>> python seed_secrets.py --app-name cloudshortener --dry-run
"""

import argparse
import json
import pathlib
from typing import Any, Dict, Iterable

import boto3
import yaml


# TODO: add retry/backoff for throttling
# TODO: add option to merge with existing secret keys instead of replace
# TODO: add allowlist/denylist of secret components to publish


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


def _gather_component_secrets(secrets_node: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    """Return a mapping of component -> secret payload dict.

    Rules:
        - Expects a mapping where keys are components (e.g., 'redis') and
          values are dicts of key/value pairs to serialize as JSON.
        - Filters out non-dict components.

    Args:
        secrets_node (Dict[str, Any]): The `secrets:` node from YAML.

    Returns:
        Dict[str, Dict[str, Any]]: component -> payload
    """
    out: Dict[str, Dict[str, Any]] = {}
    for component, payload in (secrets_node or {}).items():
        if isinstance(payload, dict):
            out[component] = payload
    return out


def _create_or_update_secret(
    sm_client,
    name: str,
    payload: Dict[str, Any],
    tags: list[dict[str, str]] | None,
    kms_key_id: str | None,
    dry_run: bool,
) -> None:
    """Create or update a secret. Never prints the secret value.

    Create path:
        create_secret(Name=name, SecretString=..., KmsKeyId=?, Tags=?)

    Update path:
        put_secret_value(SecretId=name, SecretString=...)
        tag_resource(SecretId|ARN, Tags=...)  # apply/overwrite tag keys provided

    Args:
        sm_client: boto3 Secrets Manager client.
        name (str): Secret name (not ARN), e.g., "cloudshortener/dev/shorten_url/redis".
        payload (Dict[str, Any]): Dict serialized to JSON for SecretString.
        tags (list[dict[str, str]] | None): Tags to apply.
        kms_key_id (str | None): KMS key ID/ARN or alias for encryption (optional).
        dry_run (bool): If True, only print intentions (no writes).
    """
    preview_keys = list(payload.keys())
    msg = f"SecretsManager upsert name='{name}' keys={preview_keys}"
    if dry_run:
        print("[DRY-RUN]", msg)
        return

    # Check existence
    arn = None
    exists = False
    try:
        resp = sm_client.describe_secret(SecretId=name)
        arn = resp.get("ARN")
        exists = True
    except sm_client.exceptions.ResourceNotFoundException:
        exists = False

    if not exists:
        kwargs = {
            "Name": name,
            "SecretString": json.dumps(payload),
        }
        if kms_key_id:
            kwargs["KmsKeyId"] = kms_key_id
        if tags:
            kwargs["Tags"] = tags
        resp = sm_client.create_secret(**kwargs)
        arn = resp.get("ARN")
        print(msg + " [created]")
    else:
        sm_client.put_secret_value(SecretId=name, SecretString=json.dumps(payload))
        print(msg + " [updated]")

        # Apply/overwrite provided tags on existing secret (idempotent by key)
        if tags:
            # tag_resource accepts either ARN or name; prefer ARN if we have it
            sm_client.tag_resource(SecretId=arn or name, Tags=tags)


def main(argv: list[str] | None = None) -> None:
    """CLI entry point.

    Steps:
        - Parse CLI arguments
        - Discover config YAMLs under --root
        - For each file, extract `secrets:` and publish one secret per component

    Raises:
        FileNotFoundError: when --root is not a directory.
        ValueError: when --tags is malformed or YAML contents are invalid.
        boto3/botocore exceptions: on AWS API failures.
    """
    parser = argparse.ArgumentParser(
        prog="seed_secrets.py",
        description="Publish application secrets from config/<function>/<env>.yaml to AWS Secrets Manager",
    )
    parser.add_argument(
        "--app-name",
        required=True,
        help="Application name for the secret name prefix (e.g., cloudshortener)",
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
        help='Comma-separated tags to attach, e.g. "Owner=Pesho,Service=cloudshortener"',
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
    parser.add_argument(
        "--kms-key-id",
        default=None,
        help="KMS key ID/ARN/alias for encrypting secrets (default: service-managed key)",
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

    sm = session.client("secretsmanager")

    writes = 0
    for yaml_path in _yaml_config_files(root):
        # Derive <function> and <env> from path
        function_name = yaml_path.parent.name          # e.g., "shorten_url"
        env_name = yaml_path.stem                      # e.g., "dev"

        if args.env_allow and env_name not in args.env_allow:
            continue

        doc = _load_yaml(yaml_path)
        secrets_node = doc.get("secrets") or {}

        if not isinstance(secrets_node, dict):
            raise ValueError(f"'secrets' section must be a mapping in {yaml_path}")
        if not secrets_node:
            # nothing to publish in this file; continue silently
            continue

        component_map = _gather_component_secrets(secrets_node)
        if not component_map:
            # no valid dict components under 'secrets'
            continue

        # Compose base tags; these keys apply to all components in this YAML
        base_tags = [
            {"Key": "App", "Value": app_name},
            {"Key": "Env", "Value": env_name},
            {"Key": "Function", "Value": function_name},
        ] + extra_tags

        for component, payload in sorted(component_map.items()):
            # Secret name: <AppName>/<env>/<function>/<component>
            secret_name = f"{app_name}/{env_name}/{function_name}/{component}"

            # Add component tag for easier discovery
            tags = base_tags + [{"Key": "Component", "Value": component}]

            _create_or_update_secret(
                sm_client=sm,
                name=secret_name,
                payload=payload,
                tags=tags,
                kms_key_id=args.kms_key_id,
                dry_run=args.dry_run,
            )
            writes += 1

    print(f"Done. {'Previewed' if args.dry_run else 'Wrote'} {writes} secrets.")


if __name__ == "__main__":
    # Let exceptions raise naturally; a traceback signals non-zero exit to the shell.
    main()