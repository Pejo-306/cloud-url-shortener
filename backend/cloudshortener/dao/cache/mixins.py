import json
import os

import boto3
import redis
from botocore.client import BaseClient

from cloudshortener.constants import ENV
from cloudshortener.exceptions import MalformedResponseError, BadConfigurationError
from cloudshortener.dao.cache.types import ElastiCacheParameters, ElastiCacheUserSecret
from cloudshortener.dao.cache.cache_key_schema import CacheKeySchema
from cloudshortener.dao.redis.mixins import RedisClientMixin
from cloudshortener.utils.config import running_locally
from cloudshortener.utils.helpers import require_environment
from cloudshortener.constants import ENV


class ElastiCacheClientMixin(RedisClientMixin):
    """Cache mixin for AWS ElastiCache clients.

    Use this mixin as a parent class on all DAOs that interact with AWS ElastiCache.
    The mixin resolves connection parameters from SSM and Secrets Manager and
    constructs a Redis client for use within the DAO.

    Environment variables (paths/names to resolve at runtime):
        - `ELASTICACHE_HOST_PARAM`  : SSM parameter path for Redis host
        - `ELASTICACHE_PORT_PARAM`  : SSM parameter path for Redis port
        - `ELASTICACHE_DB_PARAM`    : SSM parameter path for Redis DB index
        - `ELASTICACHE_USER_PARAM`  : SSM parameter path for Redis username (optional)
        - `ELASTICACHE_SECRET`      : Secrets Manager name for {"username": "...", "password": "..."}
        - `LOCALSTACK_ENDPOINT`     : LocalStack endpoint URL for local development

    The secret is expected to be a JSON object with fields:
        - `username`: optional string (commonly `None` for ElastiCache token auth)
        - `password`: required string (the AuthToken)
    """

    def __init__(
        self,
        prefix: str | None = None,
        ssm_client: BaseClient | None = None,
        secrets_client: BaseClient | None = None,
        redis_decode_responses: bool = True,
        tls_verify: bool = False,
        ca_bundle_path: str | None = None,
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
    @require_environment(ENV.ElastiCache.HOST_PARAM, ENV.ElastiCache.PORT_PARAM, ENV.ElastiCache.DB_PARAM)
    def _resolve_ssm_params(ssm_client: BaseClient | None) -> ElastiCacheParameters:
        """Resolve host, port, db, and optional username from SSM Parameter Store."""
        host_param = os.environ[ENV.ElastiCache.HOST_PARAM]
        port_param = os.environ[ENV.ElastiCache.PORT_PARAM]
        db_param = os.environ[ENV.ElastiCache.DB_PARAM]
        user_param = os.environ.get(ENV.ElastiCache.USER_PARAM)  # optional

        # fmt: off
        ssm_client_kwargs = {
            'endpoint_url': os.environ.get(ENV.LocalStack.ENDPOINT, 'http://localhost:4566'),
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
        except KeyError as e:
            raise MalformedResponseError('Malformed SSM get_parameter response') from e

        try:
            port = int(port_str)
            db = int(db_str)
        except (TypeError, ValueError) as e:
            raise BadConfigurationError(f'Invalid ElastiCache port/db values: port={port_str!r} db={db_str!r}') from e

        return host, port, db, user

    # TODO: decorate this with @require_environment(ENV.LocalStack.ENDPOINT, local_only=True)
    @staticmethod
    @require_environment(ENV.ElastiCache.SECRET)
    def _resolve_secret(secrets_client: BaseClient | None) -> ElastiCacheUserSecret:
        """Resolve optional username and required password from Secrets Manager."""
        secret_name = os.environ[ENV.ElastiCache.SECRET]
        # fmt: off
        secrets_client_kwargs = {
            'endpoint_url': os.environ.get(ENV.LocalStack.ENDPOINT, 'http://localhost:4566'),
        } if running_locally() else {}
        # fmt: on
        sm = secrets_client or boto3.client('secretsmanager', **secrets_client_kwargs)

        try:
            raw = sm.get_secret_value(SecretId=secret_name).get('SecretString')
            payload = json.loads(raw or '{}')
        except json.JSONDecodeError as e:
            raise MalformedResponseError('Invalid JSON in ElastiCache secret payload') from e

        username = payload.get('username')  # optional
        password = payload.get('password')  # required

        # TODO: add feature flags to enable using elasticache locally
        # then patch this monkeypatch out
        if False and not password:
            raise BadConfigurationError('ElastiCache secret must contain a non-empty "password" field')

        return username, password
