import os

import redis
from google.cloud import secretmanager

from cloudshortener.constants import ENV, GCP
from cloudshortener.exceptions import BadConfigurationError, MalformedResponseError
from cloudshortener.utils.helpers import require_environment
from cloudshortener.dao.redis.mixins import RedisClientMixin
from cloudshortener.cloud.dao.cache import CacheKeySchema
from cloudshortener.cloud.gcp.dao.cache.types import MemoryStoreAuthSecret, MemoryStoreParameters


class MemoryStoreClientMixin(RedisClientMixin):
    """Cache mixin for GCP MemoryStore.

    Use this mixin as a parent class on all DAOs that interact with GCP MemoryStore.
    The mixin resolves connection parameters from environment variables and
    Secret Manager and constructs a Redis client for use within the DAO.

    Environment variables (paths/names to resolve at runtime):
        - `GCP_PROJECT_ID`          : GCP project ID
        - `MEMORYSTORE_HOST`        : MemoryStore Redis host
        - `MEMORYSTORE_PORT`        : MemoryStore Redis port (defaults to 6379)
        - `MEMORYSTORE_AUTH_SECRET` : Secret Manager secret ID

    The secret is expected to be the raw MemoryStore AUTH string.
    """

    keys: CacheKeySchema

    def __init__(
        self,
        prefix: str | None = None,
        tls_verify: bool = False,
        secrets_client: secretmanager.SecretManagerServiceClient | None = None,
    ):
        host, port = self._resolve_env_params()
        auth_string = self._resolve_auth_secret(secrets_client)

        redis_client = redis.Redis(
            host=host,
            port=port,
            db=0,
            password=auth_string,
            decode_responses=True,
            ssl=True,
            ssl_cert_reqs='required' if tls_verify else 'none',
        )

        super().__init__(redis_client=redis_client, prefix=prefix)
        self.keys = CacheKeySchema(prefix=prefix)

    @staticmethod
    @require_environment(ENV.GCP.MEMORYSTORE_HOST)
    def _resolve_env_params() -> MemoryStoreParameters:
        host = os.environ[ENV.GCP.MEMORYSTORE_HOST]
        port_str = os.environ.get(ENV.GCP.MEMORYSTORE_PORT, str(GCP.MemoryStore.DEFAULT_PORT))

        try:
            port = int(port_str)
        except (TypeError, ValueError) as e:
            raise BadConfigurationError(f'Invalid MemoryStore port value: {port_str!r}') from e

        return host, port

    @staticmethod
    @require_environment(ENV.GCP.GCP_PROJECT_ID, ENV.GCP.MEMORYSTORE_AUTH_SECRET)
    def _resolve_auth_secret(secrets_client: secretmanager.SecretManagerServiceClient | None = None) -> MemoryStoreAuthSecret:
        project_id = os.environ[ENV.GCP.GCP_PROJECT_ID]
        secret_id = os.environ[ENV.GCP.MEMORYSTORE_AUTH_SECRET]
        secret_name = f'projects/{project_id}/secrets/{secret_id}/versions/latest'
        client = secrets_client or secretmanager.SecretManagerServiceClient()

        try:
            response = client.access_secret_version(request={'name': secret_name})
            payload = response.payload.data.decode('utf-8')
        except (AttributeError, KeyError, UnicodeDecodeError) as e:
            raise MalformedResponseError('Malformed Secret Manager access_secret_version response') from e

        if not payload:
            raise BadConfigurationError('MemoryStore auth secret must contain a non-empty value')

        return payload
