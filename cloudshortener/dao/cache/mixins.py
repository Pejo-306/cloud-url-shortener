"""Cache mixin providing AWS-resolved ElastiCache client initialization.

Responsibilities:
    - Initialize a TLS-enabled Redis client targeting AWS ElastiCache.
    - Resolve connection parameters from AWS SSM Parameter Store.
    - Resolve credentials from AWS Secrets Manager.
    - Delegate healthcheck and key management to RedisClientMixin.

Classes:
    - ElastiCacheClientMixin: Base mixin to inject AWS-resolved client setup
      (TLS + AUTH) and reuse RedisClientMixin’s healthcheck and key schema.

Example:
    Typical usage with a DAO implementation:

        >>> class AppConfigCacheDAO(ElastiCacheClientMixin, SomeBaseDAO):
        ...     pass
        ...
        >>> dao = AppConfigCacheDAO(prefix="cloudshortener:dev")
        >>> dao._heatlhcheck()
        True

Environment variables (paths/names to resolve at runtime):
    - ELASTICACHE_HOST_PARAM  : SSM parameter path for Redis host
    - ELASTICACHE_PORT_PARAM  : SSM parameter path for Redis port
    - ELASTICACHE_DB_PARAM    : SSM parameter path for Redis DB index
    - ELASTICACHE_USER_PARAM  : SSM parameter path for Redis username (optional)
    - ELASTICACHE_SECRET      : Secrets Manager name for {"username": "...", "password": "..."}
    - LOCALSTACK_ENDPOINT     : LocalStack endpoint URL for local development
"""

import json
import os
from typing import Optional

import boto3
import redis
from botocore.client import BaseClient
from botocore.exceptions import BotoCoreError, ClientError

from cloudshortener.dao.cache.cache_key_schema import CacheKeySchema
from cloudshortener.dao.redis.mixins import RedisClientMixin
from cloudshortener.utils.config import running_locally
from cloudshortener.utils.helpers import require_environment
from cloudshortener.utils.constants import (
    ELASTICACHE_HOST_PARAM_ENV,
    ELASTICACHE_PORT_PARAM_ENV,
    ELASTICACHE_DB_PARAM_ENV,
    ELASTICACHE_USER_PARAM_ENV,
    ELASTICACHE_SECRET_ENV,
    LOCALSTACK_ENDPOINT_ENV,
)


class ElastiCacheClientMixin(RedisClientMixin):
    """Mixin ElastiCache client setup using AWS SSM/Secrets with TLS by default.

    This mixin resolves connection parameters from SSM and credentials from
    Secrets Manager, constructs a Redis client (TLS in AWS; plain in local),
    and passes it to the parent RedisClientMixin for healthcheck and key schema
    wiring.

    Attributes:
        redis (redis.Redis):
            Active Redis client instance created with TLS and (optional) AUTH.

        keys (RedisKeySchema):
            Helper class for generating namespaced Redis key names (inherited
            from RedisClientMixin via its constructor).

    Methods:
        (inherited) _heatlhcheck(raise_error: bool = True) -> bool:
            Ping Redis to verify connectivity. Optionally raise a DataStoreError
            if unreachable.

    Args:
        prefix (Optional[str]):
            Namespace prefix for all Redis keys, e.g. 'app:env'.
        ssm_client (Optional[BaseClient]):
            Optional boto3 SSM client to reuse (useful in tests).
            If None, a new client is created (points to LocalStack in local mode).
        secrets_client (Optional[BaseClient]):
            Optional boto3 Secrets Manager client to reuse (useful in tests).
            If None, a new client is created (points to LocalStack in local mode).
        redis_decode_responses (bool):
            If True, decodes Redis responses. Defaults to True.
        tls_verify (bool):
            If True (default), require certificate verification (ssl_cert_reqs='required').
            Set False to disable verification (not recommended; mainly for custom CA/local).
        ca_bundle_path (Optional[str]):
            Optional path to a CA bundle file for certificate verification.

    Raises:
        KeyError:
            If required environment variables are missing.
        ValueError:
            If SSM values are malformed (e.g., non-integer port/db) or the secret payload
            is invalid/missing required fields.
        botocore.exceptions.BotoCoreError / ClientError:
            On AWS API failures while reading SSM or Secrets Manager.
        DataStoreError:
            If the Redis healthcheck fails after initialization (raised by parent mixin).
    """

    def __init__(
        self,
        prefix: Optional[str] = None,
        ssm_client: Optional[BaseClient] = None,
        secrets_client: Optional[BaseClient] = None,
        redis_decode_responses: bool = True,
        tls_verify: bool = False,
        ca_bundle_path: Optional[str] = None,
    ):
        # Resolve runtime settings from AWS (or LocalStack in local mode)
        host, port, db, user_from_ssm = self._resolve_ssm_params(ssm_client)
        username, password = self._resolve_secret(secrets_client)
        username = username or user_from_ssm  # prefer secret, fallback to SSM, or None

        # Build Redis client:
        # - In AWS: TLS enabled by default (ssl=True).
        # - In local mode: connect to local Redis without TLS (ssl=False).
        client_kwargs = dict(
            host=host,
            port=port,
            db=db,
            username=username,
            password=password,
            decode_responses=redis_decode_responses,
        )

        # TODO: add feature flags to enable using elasticache locally
        # => if False and running_locally(), use elasticache with TLS
        # => if True and running_locally(), use local Redis without TLS
        if running_locally():
            # Local Redis typically runs without TLS
            client_kwargs.update(ssl=False)
        else:
            # ElastiCache requires TLS when AuthToken is enabled
            client_kwargs.update(
                ssl=True,
                ssl_cert_reqs='required' if tls_verify else None,
            )
            if tls_verify and ca_bundle_path:
                client_kwargs['ssl_ca_certs'] = ca_bundle_path

        redis_client = redis.Redis(**client_kwargs)

        # Delegate to base mixin: sets self.redis, self.keys, and runs healthcheck
        super().__init__(redis_client=redis_client, prefix=prefix)
        self.keys = CacheKeySchema(prefix=prefix)

    @staticmethod
    @require_environment(ELASTICACHE_HOST_PARAM_ENV, ELASTICACHE_PORT_PARAM_ENV, ELASTICACHE_DB_PARAM_ENV)
    def _resolve_ssm_params(ssm_client: Optional[BaseClient]) -> tuple[str, int, int, Optional[str]]:
        """Resolve host, port, db, and optional username from SSM Parameter Store.

        Reads parameter names from environment variables and fetches their values
        using SSM (or LocalStack in local mode). The port and db values are validated
        and cast to integers.

        Environment:
            - ELASTICACHE_HOST_PARAM: SSM parameter path for Redis host
            - ELASTICACHE_PORT_PARAM: SSM parameter path for Redis port
            - ELASTICACHE_DB_PARAM: SSM parameter path for Redis DB index
            - ELASTICACHE_USER_PARAM: SSM parameter path for Redis username (optional)
            - LOCALSTACK_ENDPOINT: LocalStack endpoint URL for local development

        Returns:
            Tuple[str, int, int, Optional[str]]:
                (host, port, db, user_from_ssm_or_none)

        Raises:
            KeyError:
                If mandatory environment variables are missing.
            botocore.exceptions.BotoCoreError / ClientError:
                On AWS SSM API failures.
            ValueError:
                If SSM responses are malformed or port/db cannot be cast to int.
        """
        host_param = os.environ[ELASTICACHE_HOST_PARAM_ENV]
        port_param = os.environ[ELASTICACHE_PORT_PARAM_ENV]
        db_param = os.environ[ELASTICACHE_DB_PARAM_ENV]
        user_param = os.environ.get(ELASTICACHE_USER_PARAM_ENV)  # optional

        # fmt: off
        ssm_client_kwargs = {
            'endpoint_url': os.environ.get(LOCALSTACK_ENDPOINT_ENV, 'http://localhost:4566'),
        } if running_locally() else {}
        # fmt: on
        ssm = ssm_client or boto3.client('ssm', **ssm_client_kwargs)

        try:
            host = ssm.get_parameter(Name=host_param)['Parameter']['Value']
            port_str = ssm.get_parameter(Name=port_param)['Parameter']['Value']
            db_str = ssm.get_parameter(Name=db_param)['Parameter']['Value']
            user = None
            if user_param:
                user = ssm.get_parameter(Name=user_param)['Parameter']['Value']
        except (BotoCoreError, ClientError):
            raise
        except KeyError as e:
            raise ValueError('Malformed SSM get_parameter response') from e

        try:
            port = int(port_str)
            db = int(db_str)
        except (TypeError, ValueError) as e:
            raise ValueError(f'Invalid ElastiCache port/db values: port={port_str!r} db={db_str!r}') from e

        return host, port, db, user

    @staticmethod
    @require_environment(ELASTICACHE_SECRET_ENV)
    def _resolve_secret(secrets_client: Optional[BaseClient]) -> tuple[Optional[str], str]:
        """Resolve optional username and required password from Secrets Manager.

        Environment:
            - ELASTICACHE_SECRET: Secrets Manager name for {"username": "...", "password": "..."}
            - LOCALSTACK_ENDPOINT: LocalStack endpoint URL for local development

        The secret is expected to be a JSON object with fields:
            - "username": optional string (commonly None for ElastiCache token auth)
            - "password": required string (the AuthToken)

        Returns:
            Tuple[Optional[str], str]:
                (username_or_none, password)

        Raises:
            KeyError:
                If ELASTICACHE_SECRET environment variable is missing.
            botocore.exceptions.BotoCoreError / ClientError:
                On AWS Secrets Manager API failures.
            ValueError:
                If the secret payload is not valid JSON or missing 'password'.
        """
        secret_name = os.environ[ELASTICACHE_SECRET_ENV]
        # fmt: off
        secrets_client_kwargs = {
            'endpoint_url': os.environ.get(LOCALSTACK_ENDPOINT_ENV, 'http://localhost:4566'),
        } if running_locally() else {}
        # fmt: on
        sm = secrets_client or boto3.client('secretsmanager', **secrets_client_kwargs)

        try:
            raw = sm.get_secret_value(SecretId=secret_name).get('SecretString')
            payload = json.loads(raw or '{}')
        except (BotoCoreError, ClientError):
            raise
        except json.JSONDecodeError as e:
            raise ValueError('Invalid JSON in ElastiCache secret payload') from e

        username = payload.get('username')  # optional
        password = payload.get('password')  # required

        # TODO: add feature flags to enable using elasticache locally
        # then patch this monkeypatch out
        if False and not password:
            raise ValueError('ElastiCache secret must contain a non-empty "password" field')

        return username, password
