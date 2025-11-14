#!/usr/bin/env python3
"""
Seed SSM Parameter Store from local YAML config files.

This CLI follows this procedure to publish configuration parameters:
- Step 1: Discover YAML files in config/<function>/<env>.yaml
- Step 2: Load and validate each YAML document
- Step 3: Extract only the `params:` section (ignore `secrets:`)
- Step 4: Flatten nested keys into SSM paths
- Step 5: Upsert parameters into AWS Systems Manager Parameter Store

CLI usage:
    $ python -m bootstrap.seed_ssm_parameters --app-name cloudshortener --root config --env-allow dev prod
    $ python -m bootstrap.seed_ssm_parameters --app-name cloudshortener --dry-run
    $ python -m bootstrap.seed_ssm_parameters --app-name cloudshortener --tags "Owner=Pesho,Service=cloudshortener"
    $ python -m bootstrap.seed_ssm_parameters --app-name cloudshortener --aws-profile my-profile

AWS credentials/region:
    - Use --aws-profile to select a profile from ~/.aws/{credentials,config}.
    - If omitted, boto3’s default resolution applies (env vars, default profile, etc).

Behavior:
    - Writes parameters under: /<app>/<env>/<function>/<...>
      Example: /cloudshortener/dev/shorten_url/redis/host = "redis.example"
    - Values are stored as String (4 KB limit). Use Secrets Manager for credentials.
    - Uses correct create/update semantics for tagging (SSM forbids Tags+Overwrite together).
    - Adds optional tags and a default set of tags: App, Env, Function.

Raises:
    FileNotFoundError: If the --root directory does not exist.
    ValueError: For malformed --tags input or unexpected YAML structure.
    botocore.exceptions.BotoCoreError / ClientError: For AWS API failures.

# TODO: add structured logging and retry/backoff on throttling
# TODO: add per-key SecureString opt-in via an allowlist (kept under params, not secrets)
"""

from __future__ import annotations

import argparse
import pathlib
from typing import Any, Dict

from bootstrap.helper import (
    boto3_session,
    flatten,
    load_yaml,
    normalize_user_tags,
    yaml_config_files,
)
from bootstrap.aws_actions import put_parameter


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
        prog="seed_ssm_parameters.py",
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

    # argparse maps --app-name to args.app_name
    app_name = getattr(args, "app_name", None)
    if not app_name:
        raise ValueError("Missing required --app-name")

    root = pathlib.Path(args.root)
    if not root.is_dir():
        raise FileNotFoundError(f"Bad config root: {root}")

    extra_tags = normalize_user_tags(args.tags)
    session = boto3_session(args.aws_profile)
    ssm = session.client("ssm")

    writes = 0
    for yaml_path in yaml_config_files(root):
        function_name = yaml_path.parent.name  # e.g., "shorten_url"
        env_name = yaml_path.stem              # e.g., "dev"

        if args.env_allow and env_name not in args.env_allow:
            continue

        doc: Dict[str, Any] = load_yaml(yaml_path)
        params = doc.get("params") or {}
        if not isinstance(params, dict):
            raise ValueError(f"'params' section must be a mapping in {yaml_path}")
        if not params:
            continue  # nothing to publish

        prefix = f"/{app_name}/{env_name}/{function_name}"
        flat = flatten(prefix, params)

        # Compose tags for all keys in this YAML
        base_tags = [
            {"Key": "App", "Value": app_name},
            {"Key": "Env", "Value": env_name},
            {"Key": "Function", "Value": function_name},
        ] + extra_tags

        for name, value in sorted(flat.items()):
            put_parameter(
                ssm_client=ssm,
                name=name,
                value=value,
                tags=base_tags,
                dry_run=args.dry_run,
            )
            writes += 1

    print(f"Done. {'Previewed' if args.dry_run else 'Wrote'} {writes} parameters.")


if __name__ == "__main__":
    main()
