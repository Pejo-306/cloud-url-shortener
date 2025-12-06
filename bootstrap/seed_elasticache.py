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
    $ python -m bootstrap.seed_elasticache \
        --app-name cloudshortener --env dev \
        --host redis.example \
        --port 6379 --db 0 \
        --user default --password 'bP7f2Qk9LxN4Rz8TgH3mVw6YcJ5pK1sD' \
        --tags "Owner=Pesho,Service=cloudshortener"

    $ python -m bootstrap.seed_elasticache --app-name cloudshortener --env dev \
        --host redis.local --user default --password 'localpass' --dry-run

Behavior:
    - Creates or updates String parameters (non-secret) in SSM.
    - Creates or updates a JSON secret in Secrets Manager (username/password).
    - Applies tags only on create for SSM (SSM forbids Tags+Overwrite together).
    - Prints concise action logs; never prints secret values.

Args:
    --app-name (str): Application name for path prefix (e.g., cloudshortener).
    --env (str): Environment (e.g., dev, staging, prod).
    --host (str): ElastiCache Redis host (required).
    --port (int): ElastiCache Redis port (default: 6379).
    --db (int): Redis DB index (>= 0, default: 0).
    --user (str): Redis ACL username (required; also stored in secret).
    --password (str): Redis ACL password (required; stored only in secret).
    --tags (str): Optional comma-separated key=value tags.
    --dry-run (flag): If set, preview without writing.
    --aws-profile (str): Optional AWS shared config/credentials profile.

Returns:
    None

Raises:
    ValueError: For invalid or missing inputs.
    botocore.exceptions.BotoCoreError / ClientError: For AWS API failures.
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
    parser.add_argument('--host', required=True, help='ElastiCache Redis host')
    parser.add_argument('--port', default='6379', help='ElastiCache Redis port (default: 6379)')
    parser.add_argument('--db', default='0', help='Redis DB index (>= 0, default: 0)')
    parser.add_argument('--user', required=True, help='Redis ACL username (required)')
    parser.add_argument(
        '--password',
        required=True,
        help='Redis ACL password (required; stored only in Secrets Manager)',
    )
    parser.add_argument('--tags', default='', help='Comma-separated tags, e.g. "Owner=Pesho,Service=cloudshortener"')
    parser.add_argument('--dry-run', action='store_true', help='Preview without writing')
    parser.add_argument('--aws-profile', default=None, help='AWS shared profile name (e.g., default, dev, prod)')

    args = parser.parse_args(argv)

    app = args.app_name.strip()
    env = args.env.strip()
    host = args.host.strip()
    user = args.user.strip()
    password = args.password
    port = _positive_int('port', args.port)
    db = _positive_int('db', args.db)

    if not app:
        raise ValueError('Missing --app-name')
    if not env:
        raise ValueError('Missing --env')
    if not host:
        raise ValueError('Missing --host')
    if not user:
        raise ValueError('Missing --user')
    if password == '':
        raise ValueError('Missing --password')

    base_path = f'/{app}/{env}/elasticache'
    params = {
        f'{base_path}/host': host,
        f'{base_path}/port': str(port),
        f'{base_path}/db': str(db),
        f'{base_path}/user': user,
    }

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
    ssm = session.client('ssm')
    sm = session.client('secretsmanager')

    writes = 0
    for name, value in sorted(params.items()):
        put_parameter(
            ssm_client=ssm,
            name=name,
            value=value,
            tags=ssm_tags,
            dry_run=args.dry_run,
        )
        writes += 1

    create_or_update_secret(
        secrets_client=sm,
        name=secret_name,
        payload=secret_payload,
        tags=secret_tags,
        kms_key_id=None,
        dry_run=args.dry_run,
    )

    print(f"Done. {'Previewed' if args.dry_run else 'Wrote'} {writes} SSM parameters under {base_path} and secret '{secret_name}'.")


if __name__ == '__main__':
    main()
