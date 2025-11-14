#!/usr/bin/env python3
"""
Seed AWS Secrets Manager from local YAML config files.

This CLI follows this procedure to publish application secrets:
- Step 1: Discover YAML files in config/<function>/<env>.yaml
- Step 2: Load and validate each YAML document
- Step 3: Extract only the `secrets:` section (ignore `params:`)
- Step 4: Group secrets by top-level component (e.g., "redis")
- Step 5: Create or update one Secrets Manager secret per component

CLI usage:
    $ python -m bootstrap.seed_secrets --app-name cloudshortener --root config --env-allow dev prod
    $ python -m bootstrap.seed_secrets --app-name cloudshortener --dry-run
    $ python -m bootstrap.seed_secrets --app-name cloudshortener --tags "Owner=Pesho,Service=cloudshortener"
    $ python -m bootstrap.seed_secrets --app-name cloudshortener --aws-profile my-profile
    $ python -m bootstrap.seed_secrets --app-name cloudshortener --kms-key-id alias/aws/secretsmanager

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
        * If secret exists → update value (PutSecretValue) and apply/overwrite tags (TagResource).
    - Adds optional user tags plus: App, Env, Function, Component.

Raises:
    FileNotFoundError: If the --root directory does not exist.
    ValueError: For malformed --tags input or unexpected YAML structure.
    botocore.exceptions.BotoCoreError / ClientError: For AWS API failures.

# TODO: add retry/backoff for throttling
# TODO: add option to merge with existing secret keys instead of replace
# TODO: add allowlist/denylist of secret components to publish
"""

from __future__ import annotations

import argparse
import pathlib
from typing import Any, Dict, Iterable

from bootstrap.helper import (
    boto3_session,
    load_yaml,
    normalize_user_tags,
    yaml_config_files,
)
from bootstrap.aws_actions import create_or_update_secret


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

    app_name = getattr(args, "app_name", None)
    if not app_name:
        raise ValueError("Missing required --app-name")

    root = pathlib.Path(args.root)
    if not root.is_dir():
        raise FileNotFoundError(f"Bad config root: {root}")

    extra_tags = normalize_user_tags(args.tags)
    session = boto3_session(args.aws_profile)
    sm = session.client("secretsmanager")

    writes = 0
    for yaml_path in yaml_config_files(root):
        function_name = yaml_path.parent.name  # e.g., "shorten_url"
        env_name = yaml_path.stem              # e.g., "dev"

        if args.env_allow and env_name not in args.env_allow:
            continue

        doc: Dict[str, Any] = load_yaml(yaml_path)
        secrets_node = doc.get("secrets") or {}
        if not isinstance(secrets_node, dict):
            raise ValueError(f"'secrets' section must be a mapping in {yaml_path}")
        if not secrets_node:
            continue  # nothing to publish

        component_map = _gather_component_secrets(secrets_node)
        if not component_map:
            continue

        # Base tags shared across this YAML file
        base_tags = [
            {"Key": "App", "Value": app_name},
            {"Key": "Env", "Value": env_name},
            {"Key": "Function", "Value": function_name},
        ] + extra_tags

        for component, payload in sorted(component_map.items()):
            secret_name = f"{app_name}/{env_name}/{function_name}/{component}"
            tags = base_tags + [{"Key": "Component", "Value": component}]

            create_or_update_secret(
                secrets_client=sm,
                name=secret_name,
                payload=payload,
                tags=tags,
                kms_key_id=args.kms_key_id,
                dry_run=args.dry_run,
            )
            writes += 1

    print(f"Done. {'Previewed' if args.dry_run else 'Wrote'} {writes} secrets.")


if __name__ == "__main__":
    main()
