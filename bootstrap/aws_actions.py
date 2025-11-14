"""
AWS action primitives for seeding configuration.

This module encapsulates AWS SDK calls used by the seeding CLIs.

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

Behavior:
    - `put_parameter`:
        * Creates or updates a String parameter.
        * Applies tags only on create (SSM forbids Tags+Overwrite together).
        * Never returns secret material; prints concise action logs.

    - `create_or_update_secret`:
        * Creates a secret with optional KMS key and tags, or updates value if it exists.
        * Applies/overwrites provided tag keys on existing secrets via TagResource.
        * Never prints secret payload.

Raises:
    botocore.exceptions.BotoCoreError / ClientError for AWS API failures.

Example:
    >>> # SSM example (no dry-run)
    >>> put_parameter(ssm_client=ssm, name="/app/dev/svc/redis/host", value="redis.example")
    >>> # Secrets example (dry-run)
    >>> create_or_update_secret(secrets_client=sm, name="app/dev/svc/redis",
    ...                         payload={"username": "u", "password": "p"}, dry_run=True)
"""

from __future__ import annotations

import json
from typing import Any, Dict, List, Optional


def put_parameter(
    ssm_client,
    name: str,
    value: str,
    *,
    tags: Optional[List[Dict[str, str]]] = None,
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
        print("[DRY-RUN]", msg)
        return

    exists = False
    try:
        ssm_client.get_parameter(Name=name)
        exists = True
    except ssm_client.exceptions.ParameterNotFound:
        exists = False

    if exists:
        # Update existing parameter (no tags)
        ssm_client.put_parameter(Name=name, Type="String", Value=value, Overwrite=True)
        print(msg + " [updated]")
    else:
        # Create new parameter (tags allowed on create)
        kwargs = {"Name": name, "Type": "String", "Value": value}
        if tags:
            kwargs["Tags"] = tags
        ssm_client.put_parameter(**kwargs)
        print(msg + " [created]")


def create_or_update_secret(
    secrets_client,
    name: str,
    payload: Dict[str, Any],
    *,
    tags: Optional[List[Dict[str, str]]] = None,
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
        payload (Dict[str, Any]):
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
        print("[DRY-RUN]", msg)
        return

    # Existence check
    arn = None
    exists = False
    try:
        resp = secrets_client.describe_secret(SecretId=name)
        arn = resp.get("ARN")
        exists = True
    except secrets_client.exceptions.ResourceNotFoundException:
        exists = False

    if not exists:
        kwargs = {"Name": name, "SecretString": json.dumps(payload)}
        if kms_key_id:
            kwargs["KmsKeyId"] = kms_key_id
        if tags:
            kwargs["Tags"] = tags
        resp = secrets_client.create_secret(**kwargs)
        arn = resp.get("ARN")
        print(msg + " [created]")
    else:
        secrets_client.put_secret_value(SecretId=name, SecretString=json.dumps(payload))
        print(msg + " [updated]")
        if tags:
            secrets_client.tag_resource(SecretId=arn or name, Tags=tags)
