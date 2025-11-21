#!/usr/bin/env python3
"""
Provision or remove the OIDC bootstrap CloudFormation stack.

This CLI drives a small, idempotent CFN workflow to manage GitHub OIDC identities:
- Step 1: Read a local CloudFormation template (TemplateBody mode)
- Step 2: Create a Change Set (CREATE or UPDATE) with parameter defaults
- Step 3: Optionally execute the Change Set and stream stack events every 5 seconds
- Step 4: Support deletion with event streaming

CLI usage:
    $ python -m bootstrap.bootstrap_oidc up \
        --stack-name cloudshortener-bootstrap \
        --aws-profile personal-dev \
        --github-org Pejo-306 \
        --repo cloud-url-shortener
    $ python -m bootstrap.bootstrap_oidc down --stack-name cloudshortener-bootstrap --aws-profile personal-dev

AWS credentials/region:
    - Use --aws-profile to select a profile from ~/.aws/{credentials,config}.
    - If omitted, boto3’s default resolution applies (env vars, default profile, etc).
"""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Optional

from bootstrap.helper import boto3_session, parameter_overrides
from bootstrap.aws_actions import deploy_stack_with_changeset, delete_stack

DEFAULT_TEMPLATE_FILE = 'bootstrap/template.yaml'
DEFAULT_CAPABILITIES = ['CAPABILITY_IAM', 'CAPABILITY_NAMED_IAM']

DEFAULT_PARAMS: dict[str, str] = {
    'AllowedBranchGlob': 'release-*',
    'ExistingOidcProviderArn': '',
    'OidcUrl': 'https://token.actions.githubusercontent.com',
    'OidcClientIdList': 'sts.amazonaws.com',
    'OidcThumbprints': '',
    'DeployRoleName': 'github-oidc-deploy-cloudshortener',
    'ExecRoleName': 'cloudformation-exec-cloudshortener',
}


def _read_template(template_file: str) -> str:
    p = Path(template_file)
    if not p.exists():
        raise FileNotFoundError(f'Template not found: {p}')
    body = p.read_text(encoding='utf-8')
    if len(body.encode('utf-8')) > 51200:
        raise ValueError('Template > 51,200 bytes. Upload to S3 and use TemplateURL.')
    return body


def main(argv: Optional[list[str]] = None) -> None:
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        prog='bootstrap_oidc.py',
        description='Create/Update or Delete the OIDC bootstrap CloudFormation stack.',
    )
    parser.add_argument('action', help='up=create/update, down=delete')
    parser.add_argument('--aws-profile', default=None, help='AWS shared config/credentials profile name')
    parser.add_argument('--stack-name', required=True, help='Target CloudFormation stack name (required)')
    parser.add_argument('--template-file', default=DEFAULT_TEMPLATE_FILE)
    parser.add_argument('--github-org', help='GitHub organization name (required for up)')
    parser.add_argument('--repo', help='GitHub repository name (required for up)')
    parser.add_argument(
        '--parameter-overrides',
        default='',
        help='Comma-separated CloudFormation ParameterKey=Value list, e.g. "A=B,C=D,E="',
    )
    parser.add_argument('--dry-run', action='store_true', help='Preview without applying changes')
    parser.add_argument('--no-watch', action='store_true', help='Do not stream stack events')
    parser.add_argument('--poll', type=int, default=5, help='Event polling interval in seconds (default: 5)')

    args = parser.parse_args(argv)

    params: dict[str, str] = dict(DEFAULT_PARAMS)
    if args.action == 'up':
        if not args.github_org or not args.repo:
            raise ValueError("--github-org and --repo are required for action 'up'.")
        params['GitHubOrg'] = args.github_org
        params['RepoName'] = args.repo

    if args.parameter_overrides:
        params.update(parameter_overrides(args.parameter_overrides))

    session = boto3_session(args.aws_profile)
    cfn = session.client('cloudformation')

    if args.action == 'up':
        template_body = _read_template(args.template_file)
        deploy_stack_with_changeset(
            cfn_client=cfn,
            stack_name=args.stack_name,
            template_body=template_body,
            parameters=params,
            capabilities=DEFAULT_CAPABILITIES,
            dry_run=args.dry_run,
            watch=not args.no_watch,
            poll_seconds=args.poll,
        )
    elif args.action == 'down':
        confirm = input(f"Are you sure you want to delete the stack '{args.stack_name}'? [y/N]: ").strip().lower()
        if confirm not in ('y', 'yes'):
            print('Deletion cancelled.')
            return
        delete_stack(
            cfn_client=cfn,
            stack_name=args.stack_name,
            dry_run=args.dry_run,
            watch=not args.no_watch,
            poll_seconds=args.poll,
        )
    else:
        raise ValueError("action must be either 'up' or 'down'.")


if __name__ == '__main__':
    main()
