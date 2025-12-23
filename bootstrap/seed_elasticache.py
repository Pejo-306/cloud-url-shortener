#!/usr/bin/env python3
"""
Seed shared ElastiCache connection parameters and credentials.

This CLI writes environment-scoped parameters under SSM:
    /<app>/<env>/elasticache/host
    /<app>/<env>/elasticache/port
    /<app>/<env>/elasticache/db
    /<app>/<env>/elasticache/user

And creates/updates a Secrets Manager secret:
    cloudshortener/dev/elasticache/credentials
    {
        "username": "<user>",
        "password": "<password>"
    }

CLI usage:
    # Full mode: SSM + Secrets (default)
    $ python -m bootstrap.seed_elasticache \
        --app-name cloudshortener --env dev \
        --host redis.example \
        --port 6379 --db 0 \
        --user default --password 'bP7f2Qk9LxN4Rz8TgH3mVw6YcJ5pK1sD' \
        --tags "Owner=Pesho,Service=cloudshortener"

    # Secrets-only mode: only secretsmanager is updated, SSM untouched
    $ python -m bootstrap.seed_elasticache \
        --secrets-only \
        --app-name cloudshortener --env dev \
        --user default \
        --password 'bP7f2Qk9LxN4Rz8TgH3mVw6YcJ5pK1sD'

    # SSM-only mode: only SSM parameters are updated, secret untouched
    $ python -m bootstrap.seed_elasticache \
        --ssm-only \
        --app-name cloudshortener --env dev \
        --host redis.example \
        --port 6379 \
        --db 0 \
        --user default

Behavior:
    - Default (no mode flags): creates or updates SSM parameters and secrets.
    - --secrets-only: creates or updates only the JSON secret in Secrets Manager.
    - --ssm-only: creates or updates only the SSM String parameters; secret is not touched.
    - Applies tags only on create for SSM (SSM forbids Tags+Overwrite together).
    - Prints concise action logs; never prints secret values.

Args:
    --app-name (str): Application name for path prefix (e.g., cloudshortener).
    --env (str): Environment (e.g., dev, staging, prod).

    Full / default mode (no *-only flags):
        --host (str): ElastiCache Redis host (required).
        --port (int): ElastiCache Redis port (default: 6379).
        --db (int): Redis DB index (>= 0, default: 0).
        --user (str): Redis ACL username (required; also stored in secret).
        --password (str): Redis ACL password (required; stored only in secret).

    --secrets-only mode:
        Requires only:
            --app-name, --env, --user, --password

    --ssm-only mode:
        Requires only:
            --app-name, --env, --host
        Optional:
            --port (int, default: 6379)
            --db (int, default: 0)
            --user (str, optional; SSM /user param written only if provided)
        Ignores:
            --password (if provided)

    Common:
        --tags (str): Optional comma-separated key=value tags.
        --dry-run (flag): If set, preview without writing.
        --aws-profile (str): Optional AWS shared config/credentials profile.
        --secrets-only (flag): Update only Secrets Manager, skip SSM.
        --ssm-only (flag): Update only SSM parameters, skip Secrets Manager.

Returns:
    None

Raises:
    ValueError: For invalid or missing inputs.
    botocore.exceptions.BotoCoreError / ClientError: For AWS API failures.

NOTE: The ElastiCache password must be 32-128 printable ASCII characters, no
      spaces, no */*, *"*, *@* characters with at least one uppercase letter & one digit.
      Otherwise, the stack deployment will fail. Example password: `bP7f2Qk9LxN4Rz8TgH3mVw6YcJ5pK1sD`.
"""

from __future__ import annotations

import argparse

from bootstrap.helper import boto3_session, normalize_user_tags
from bootstrap.aws_actions import put_parameter, create_or_update_secret


def _positive_int(name: str, value: str) -> int:
    try:
        iv = int(value)
    except ValueError:
        raise ValueError(f'--{name} must be an integer') from None
    if iv < 0:
        raise ValueError(f'--{name} must be >= 0')
    return iv


def main(argv: list[str] | None = None) -> None:
    """CLI entry point.

    Steps:
        - Parse CLI arguments
        - Determine operating mode (full, secrets-only, ssm-only)
        - Build SSM parameter and Secrets Manager paths
        - Write (or preview) parameters and secret with idempotent upserts

    Raises:
        ValueError: when inputs are invalid or missing.
        boto3/botocore exceptions: on AWS API failures.
    """
    parser = argparse.ArgumentParser(
        prog='seed_elasticache_params.py',
        description='Publish ElastiCache connection parameters (SSM) and credentials (Secrets Manager)',
    )
    parser.add_argument('--app-name', required=True, help='Application name (e.g., cloudshortener)')
    parser.add_argument('--env', required=True, help='Environment name (e.g., dev, staging, prod)')

    # Mode selection (mutually exclusive)
    mode_group = parser.add_mutually_exclusive_group()
    mode_group.add_argument(
        '--secrets-only',
        action='store_true',
        help='Only create/update the Secrets Manager secret (skip SSM parameters)',
    )
    mode_group.add_argument(
        '--ssm-only',
        action='store_true',
        help='Only create/update SSM parameters (skip Secrets Manager secret)',
    )

    # Optional here; requiredness enforced manually based on mode
    parser.add_argument('--host', help='ElastiCache Redis host')
    parser.add_argument('--port', default='6379', help='ElastiCache Redis port (default: 6379)')
    parser.add_argument('--db', default='0', help='Redis DB index (>= 0, default: 0)')
    parser.add_argument('--user', help='Redis ACL username')
    parser.add_argument(
        '--password',
        help='Redis ACL password (stored only in Secrets Manager; required unless --ssm-only)',
    )
    parser.add_argument('--tags', default='', help='Comma-separated tags, e.g. "Owner=Pesho,Service=cloudshortener"')
    parser.add_argument('--dry-run', action='store_true', help='Preview without writing')
    parser.add_argument('--aws-profile', default=None, help='AWS shared profile name (e.g., default, dev, prod)')

    args = parser.parse_args(argv)

    app = args.app_name.strip()
    env = args.env.strip()
    host = (args.host or '').strip()
    user = (args.user or '').strip()
    password = args.password
    port = _positive_int('port', args.port)
    db = _positive_int('db', args.db)

    secrets_only = args.secrets_only
    ssm_only = args.ssm_only

    if not app:
        raise ValueError('Missing --app-name')
    if not env:
        raise ValueError('Missing --env')

    # Validate required arguments based on mode
    if secrets_only:
        # Only secret will be updated
        if not user:
            raise ValueError('--user is required when using --secrets-only')
        if password is None or password == '':
            raise ValueError('--password is required when using --secrets-only')
    elif ssm_only:
        # Only SSM parameters will be updated
        if not host:
            raise ValueError('--host is required when using --ssm-only')
        # user is optional; password is ignored in this mode
    else:
        # Default/full mode: both SSM + Secrets
        if not host:
            raise ValueError('Missing --host (required unless --secrets-only)')
        if not user:
            raise ValueError('Missing --user (required unless --ssm-only)')
        if password is None or password == '':
            raise ValueError('Missing --password (required unless --ssm-only)')

    base_path = f'/{app}/{env}/elasticache'

    # Build SSM parameters only if we are not in secrets-only mode
    params: dict[str, str] = {}
    if not secrets_only:
        params[f'{base_path}/host'] = host
        params[f'{base_path}/port'] = str(port)
        params[f'{base_path}/db'] = str(db)
        if user:
            # In --ssm-only mode, /user is written only if provided
            params[f'{base_path}/user'] = user

    # Build secret payload only if we are not in ssm-only mode
    secret_name = None
    secret_payload = None
    if not ssm_only:
        secret_name = f'{app}/{env}/elasticache/credentials'
        secret_payload = {'username': user, 'password': password}

    extra_tags = normalize_user_tags(args.tags)
    ssm_tags = [
        {'Key': 'App', 'Value': app},
        {'Key': 'Env', 'Value': env},
        {'Key': 'Component', 'Value': 'elasticache'},
    ] + extra_tags
    secret_tags = [
        {'Key': 'App', 'Value': app},
        {'Key': 'Env', 'Value': env},
        {'Key': 'Component', 'Value': 'elasticache'},
        {'Key': 'ManagedBy', 'Value': 'bootstrap'},
    ] + extra_tags

    session = boto3_session(args.aws_profile)

    writes = 0

    # SSM writes (skip if secrets-only)
    if not secrets_only and params:
        ssm = session.client('ssm')
        for name, value in sorted(params.items()):
            put_parameter(
                ssm_client=ssm,
                name=name,
                value=value,
                tags=ssm_tags,
                dry_run=args.dry_run,
            )
            writes += 1

    # Secret write (skip if ssm-only)
    if not ssm_only and secret_name and secret_payload:
        sm = session.client('secretsmanager')
        create_or_update_secret(
            secrets_client=sm,
            name=secret_name,
            payload=secret_payload,
            tags=secret_tags,
            kms_key_id=None,
            dry_run=args.dry_run,
        )

    # Summary message
    if secrets_only:
        action = 'Previewed' if args.dry_run else 'Wrote'
        print(f"Done. {action} secret '{secret_name}'.")
    elif ssm_only:
        action = 'Previewed' if args.dry_run else 'Wrote'
        print(f'Done. {action} {writes} SSM parameters under {base_path}.')
    else:
        action = 'Previewed' if args.dry_run else 'Wrote'
        print(f"Done. {action} {writes} SSM parameters under {base_path} and secret '{secret_name}'.")


if __name__ == '__main__':
    main()
