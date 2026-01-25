"""
AWS action primitives for seeding configuration and CloudFormation stack management.

This module encapsulates AWS SDK calls used by bootstrap CLIs:
    - SSM Parameter Store upserts
    - Secrets Manager upserts
    - CloudFormation deploy/delete using Change Sets with live event streaming

Exposed functions (signatures):
    put_parameter(
        ssm_client,
        name: str,
        value: str,
        *,
        tags: list[dict[str, str]] | None = None,
        dry_run: bool = False,
    ) -> None

    create_or_update_secret(
        secrets_client,
        name: str,
        payload: dict[str, Any],
        *,
        tags: list[dict[str, str]] | None = None,
        kms_key_id: str | None = None,
        dry_run: bool = False,
    ) -> None

    deploy_stack_with_changeset(
        cfn_client,
        *,
        stack_name: str,
        template_body: str,
        parameters: dict[str, str],
        capabilities: list[str],
        dry_run: bool = False,
        watch: bool = True,
        poll_seconds: int = 5,
    ) -> None

    delete_stack(
        cfn_client,
        *,
        stack_name: str,
        dry_run: bool = False,
        watch: bool = True,
        poll_seconds: int = 5,
    ) -> None

Behavior:
    - `put_parameter`:
        * Creates or updates a String parameter.
        * Applies tags only on create (SSM forbids Tags+Overwrite together).
        * Never returns secret material; prints concise action logs.

    - `create_or_update_secret`:
        * Creates a secret with optional KMS key and tags, or updates value if it exists.
        * Applies/overwrites provided tag keys on existing secrets via TagResource.
        * Never prints secret payload.

    - `deploy_stack_with_changeset`:
        * Creates a CloudFormation Change Set (CREATE or UPDATE).
        * Prints planned changes; executes unless dry-run.
        * Streams live events every few seconds until completion.

    - `delete_stack`:
        * Deletes an existing stack.
        * Optionally streams live events until deletion completes.

Raises:
    botocore.exceptions.BotoCoreError / ClientError: For AWS API failures.

Examples:
    >>> # SSM example (no dry-run)
    >>> put_parameter(ssm_client=ssm, name="/app/dev/svc/redis/host", value="redis.example")
    >>> # Secrets example (dry-run)
    >>> create_or_update_secret(secrets_client=sm, name="app/dev/svc/redis",
    ...                         payload={"username": "u", "password": "p"}, dry_run=True)
    >>> # CloudFormation deploy (dry-run)
    >>> deploy_stack_with_changeset(cfn_client=cfn, stack_name="bootstrap", template_body=tmpl,
    ...                             parameters={"Key":"Value"}, capabilities=["CAPABILITY_IAM"], dry_run=True)
    >>> # CloudFormation delete (watch events)
    >>> delete_stack(cfn_client=cfn, stack_name="bootstrap", watch=True)
"""

from __future__ import annotations

import json
import time
from typing import Any, Optional

from botocore.exceptions import ClientError


# ---------------------------
# SSM Parameter Store actions
# ---------------------------


def put_parameter(
    ssm_client,
    name: str,
    value: str,
    *,
    tags: Optional[list[dict[str, str]]] = None,
    dry_run: bool = False,
) -> None:
    """Create or update a String SSM parameter with correct tagging semantics.

    Steps:
        - Check if the parameter exists (GetParameter).
        - If new: create with Tags (no Overwrite).
        - If existing: update value with Overwrite=True (no Tags).
        - Print a concise action log; never prints sensitive values.

    Args:
        ssm_client:
            Boto3 Systems Manager client.
        name (str):
            Full parameter path (e.g., "/cloudshortener/dev/shorten_url/redis/host").
        value (str):
            Parameter value (<= 4 KB). Values are treated as non-secret here.
        tags (list[dict[str, str]] | None):
            Tags to attach on create. SSM does not accept Tags with Overwrite=True.
        dry_run (bool):
            If True, print intent without performing any write.

    Returns:
        None

    Raises:
        botocore.exceptions.BotoCoreError / ClientError: On AWS API failures.

    Example:
        >>> put_parameter(ssm, "/a/b/c", "v", tags=[{"Key":"Owner","Value":"Pesho"}])  # doctest: +SKIP
    """
    msg = f"SSM upsert name='{name}'"
    if dry_run:
        print('[DRY-RUN]', msg)
        return

    exists = False
    try:
        ssm_client.get_parameter(Name=name)
        exists = True
    except ssm_client.exceptions.ParameterNotFound:
        exists = False

    if exists:
        ssm_client.put_parameter(Name=name, Type='String', Value=value, Overwrite=True)
        print(msg + ' [updated]')
    else:
        kwargs = {'Name': name, 'Type': 'String', 'Value': value}
        if tags:
            kwargs['Tags'] = tags
        ssm_client.put_parameter(**kwargs)
        print(msg + ' [created]')


# ------------------------
# Secrets Manager actions
# ------------------------


def create_or_update_secret(
    secrets_client,
    name: str,
    payload: dict[str, Any],
    *,
    tags: Optional[list[dict[str, str]]] = None,
    kms_key_id: Optional[str] = None,
    dry_run: bool = False,
) -> None:
    """Create or update an AWS Secrets Manager secret (value-only logs).

    Steps:
        - Check if the secret exists (DescribeSecret).
        - If new: CreateSecret(Name, SecretString, KmsKeyId?, Tags?).
        - If existing: PutSecretValue(SecretId, SecretString), then TagResource.
        - Never prints secret values; logs the secret name and top-level keys only.

    Args:
        secrets_client:
            Boto3 Secrets Manager client.
        name (str):
            Secret name (not ARN), e.g., "cloudshortener/dev/shorten_url/redis".
        payload (dict[str, Any]):
            Secret data serialized to JSON (e.g., {"username": "...", "password": "..."}).
        tags (list[dict[str, str]] | None):
            Tags to apply. On existing secrets, keys are overwritten via TagResource.
        kms_key_id (str | None):
            KMS key ID/ARN/alias. If None, service-managed key is used.
        dry_run (bool):
            If True, print intent without performing any write.

    Returns:
        None

    Raises:
        botocore.exceptions.BotoCoreError / ClientError: On AWS API failures.

    Example:
        >>> create_or_update_secret(sm, "app/dev/svc/redis", {"username":"u","password":"p"})  # doctest: +SKIP
    """
    preview_keys = list(payload.keys())
    msg = f"Secrets upsert name='{name}' keys={preview_keys}"
    if dry_run:
        print('[DRY-RUN]', msg)
        return

    arn = None
    exists = False
    try:
        resp = secrets_client.describe_secret(SecretId=name)
        arn = resp.get('ARN')
        exists = True
    except secrets_client.exceptions.ResourceNotFoundException:
        exists = False

    if not exists:
        kwargs = {'Name': name, 'SecretString': json.dumps(payload)}
        if kms_key_id:
            kwargs['KmsKeyId'] = kms_key_id
        if tags:
            kwargs['Tags'] = tags
        resp = secrets_client.create_secret(**kwargs)
        arn = resp.get('ARN')
        print(msg + ' [created]')
    else:
        secrets_client.put_secret_value(SecretId=name, SecretString=json.dumps(payload))
        print(msg + ' [updated]')
        if tags:
            secrets_client.tag_resource(SecretId=arn or name, Tags=tags)


# ---------------------------------------
# CloudFormation (deploy/delete/watch)
# ---------------------------------------

_TERMINAL_STATUSES = {
    'CREATE_COMPLETE',
    'CREATE_FAILED',
    'ROLLBACK_COMPLETE',
    'ROLLBACK_FAILED',
    'UPDATE_COMPLETE',
    'UPDATE_COMPLETE_CLEANUP_IN_PROGRESS',  # transient, but treat as near-terminal
    'UPDATE_ROLLBACK_COMPLETE',
    'UPDATE_ROLLBACK_FAILED',
    'IMPORT_COMPLETE',
    'IMPORT_ROLLBACK_COMPLETE',
    'DELETE_COMPLETE',
    'DELETE_FAILED',
}


def _stack_exists(cfn_client, stack_name: str) -> bool:
    """Return True if stack exists, False otherwise."""
    try:
        cfn_client.describe_stacks(StackName=stack_name)
        return True
    except ClientError as e:
        if 'does not exist' in str(e):
            return False
        raise


def _current_status(cfn_client, stack_name: str) -> str | None:
    """Return the stack status string, or None if the stack does not exist."""
    try:
        stacks = cfn_client.describe_stacks(StackName=stack_name)['Stacks']
        if not stacks:
            return None
        return stacks[0]['StackStatus']
    except ClientError as e:
        if 'does not exist' in str(e):
            return None
        raise


def _param_list(params: dict[str, str]) -> list[dict[str, str]]:
    """Convert a dict of parameters into CloudFormation's required list format."""
    return [{'ParameterKey': k, 'ParameterValue': str(v)} for k, v in params.items()]


def _stream_events(cfn_client, stack_name: str, poll_seconds: int) -> None:
    """Continuously print new CloudFormation stack events and exit on terminal status."""
    seen: set[str] = set()
    while True:
        try:
            events = cfn_client.describe_stack_events(StackName=stack_name)['StackEvents']
        except ClientError:
            # During creation/deletion, describe_stack_events may briefly fail; retry.
            time.sleep(poll_seconds)
            continue

        for ev in events:
            evid = ev['EventId']
            if evid in seen:
                continue
            seen.add(evid)
            ts = ev['Timestamp'].strftime('%Y-%m-%d %H:%M:%S')
            rid = ev.get('LogicalResourceId', '')
            rtype = ev.get('ResourceType', '')
            status = ev.get('ResourceStatus', '')
            reason = ev.get('ResourceStatusReason', '')
            line = f'{ts} | {status:>24} | {rid:40} | {rtype}'
            if reason:
                line += f' | {reason}'
            print(line)

        # Termination condition
        status = _current_status(cfn_client, stack_name)
        if (status is None) or (status in _TERMINAL_STATUSES):
            return

        time.sleep(poll_seconds)


def deploy_stack_with_changeset(
    *,
    cfn_client,
    stack_name: str,
    template_body: str,
    parameters: dict[str, str],
    capabilities: list[str],
    dry_run: bool = False,
    watch: bool = True,
    poll_seconds: int = 5,
) -> None:
    """Create or update a CloudFormation stack via Change Set.

    Steps:
        - Detect stack existence to choose CREATE or UPDATE.
        - Create Change Set and wait until it’s ready.
        - Print summarized planned changes.
        - Execute Change Set (unless dry-run).
        - Stream live stack events until completion.

    Args:
        cfn_client:
            Boto3 CloudFormation client.
        stack_name (str):
            Target CloudFormation stack name.
        template_body (str):
            Template content (YAML/JSON). Max 51,200 bytes for TemplateBody.
        parameters (dict[str, str]):
            Stack parameters passed as key/value pairs.
        capabilities (list[str]):
            CloudFormation capabilities (e.g., ["CAPABILITY_IAM"]).
        dry_run (bool):
            If True, only preview changes (does not execute Change Set).
        watch (bool):
            If True, print live stack events every few seconds.
        poll_seconds (int):
            Event polling interval (default: 5 seconds).

    Returns:
        None

    Raises:
        botocore.exceptions.BotoCoreError / ClientError: On AWS API failures.
        RuntimeError: When Change Set creation fails for non-trivial reasons.
    """
    change_set_type = 'UPDATE' if _stack_exists(cfn_client, stack_name) else 'CREATE'
    cs_name = f'{stack_name}-cs-{int(time.time())}'

    resp = cfn_client.create_change_set(
        StackName=stack_name,
        ChangeSetName=cs_name,
        ChangeSetType=change_set_type,
        TemplateBody=template_body,
        Parameters=_param_list(parameters),
        Capabilities=capabilities,
    )
    cs_arn = resp['Id']

    # Wait for Change Set creation
    while True:
        desc = cfn_client.describe_change_set(ChangeSetName=cs_arn)
        status = desc['Status']
        reason = desc.get('StatusReason', '')
        if status == 'CREATE_COMPLETE':
            break
        if status == 'FAILED':
            if "didn't contain changes" in reason:
                print('No changes to apply.')
                return
            raise RuntimeError(f'Change Set failed: {reason}')
        time.sleep(2)

    # Print diff summary
    changes = desc.get('Changes', [])
    if changes:
        print('Planned changes:')
        for c in changes:
            rc = c['ResourceChange']
            act = rc.get('Action', '')
            lid = rc.get('LogicalResourceId', '')
            rtype = rc.get('ResourceType', '')
            print(f'  - {act} {lid} ({rtype})')
    else:
        print('Change Set ready (no listed changes).')

    if dry_run:
        print(f"[DRY-RUN] Created Change Set '{cs_name}' but not executing.")
        return

    print('Executing Change Set...')
    cfn_client.execute_change_set(ChangeSetName=cs_arn)

    if watch:
        try:
            _stream_events(cfn_client, stack_name, poll_seconds)
        except KeyboardInterrupt:
            pass

    waiter_name = 'stack_update_complete' if change_set_type == 'UPDATE' else 'stack_create_complete'
    waiter = cfn_client.get_waiter(waiter_name)
    waiter.wait(StackName=stack_name)
    print('Stack operation completed.')


def delete_stack(
    *,
    cfn_client,
    stack_name: str,
    dry_run: bool = False,
    watch: bool = True,
    poll_seconds: int = 5,
) -> None:
    """Delete a CloudFormation stack and optionally stream its events.

    Steps:
        - Check for stack existence.
        - Request deletion.
        - Optionally stream live deletion events until complete.

    Args:
        cfn_client:
            Boto3 CloudFormation client.
        stack_name (str):
            Target stack name to delete.
        dry_run (bool):
            If True, print intent only (no action).
        watch (bool):
            If True, stream stack events during deletion.
        poll_seconds (int):
            Event polling interval (default: 5 seconds).

    Returns:
        None

    Raises:
        botocore.exceptions.BotoCoreError / ClientError: On AWS API failures.
    """
    if dry_run:
        print(f"[DRY-RUN] Would delete stack '{stack_name}'.")
        return

    if not _stack_exists(cfn_client, stack_name):
        print(f"Stack '{stack_name}' does not exist.")
        return

    print(f"Deleting stack '{stack_name}'...")
    cfn_client.delete_stack(StackName=stack_name)

    if watch:
        try:
            _stream_events(cfn_client, stack_name, poll_seconds)
        except KeyboardInterrupt:
            pass

    # If streaming already ended because the stack disappeared, waiter will raise;
    # guard by checking existence again.
    if _stack_exists(cfn_client, stack_name):
        waiter = cfn_client.get_waiter('stack_delete_complete')
        waiter.wait(StackName=stack_name)

    print('Stack deleted.')
