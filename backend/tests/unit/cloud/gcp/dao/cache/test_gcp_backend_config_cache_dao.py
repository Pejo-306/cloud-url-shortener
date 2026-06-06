import json
from typing import cast
from unittest.mock import ANY, MagicMock, Mock, call

import pytest
import redis
from google.cloud import secretmanager, storage
from pytest import MonkeyPatch

from cloudshortener.cloud.dao.cache.constants import CacheTTL
from cloudshortener.cloud.gcp.dao.cache.gcp_backend_config_cache_dao import GCPBackendConfigCacheDAO
from cloudshortener.constants import ENV
from cloudshortener.exceptions import BadConfigurationError
from cloudshortener.types import BackendConfig


class TestGCPBackendConfigCacheDAO:
    config_document: BackendConfig
    blob: storage.Blob
    bucket: storage.Bucket
    storage_client: storage.Client
    secrets_client: secretmanager.SecretManagerServiceClient
    redis_client: redis.Redis

    @pytest.fixture
    def config_document(self) -> BackendConfig:
        return {
            'build': 3,
            'active_backend': 'redis',
            'configs': {'redirect_url': {'redis': {'host': 'h', 'port': 6379, 'db': 0}}},
        }

    @pytest.fixture
    def blob(self, config_document: BackendConfig) -> storage.Blob:
        blob = Mock(spec=storage.Blob)
        blob.download_as_text.return_value = json.dumps(config_document)
        blob.etag = 'etag-123'
        blob.content_type = 'application/json'
        return cast(storage.Blob, blob)

    @pytest.fixture
    def bucket(self, blob: storage.Blob) -> storage.Bucket:
        bucket = Mock(spec=storage.Bucket)
        bucket.blob.return_value = blob
        return cast(storage.Bucket, bucket)

    @pytest.fixture
    def storage_client(self, bucket: storage.Bucket) -> storage.Client:
        client = Mock(spec=storage.Client)
        client.bucket.return_value = bucket
        return cast(storage.Client, client)

    @pytest.fixture
    def secrets_client(self) -> secretmanager.SecretManagerServiceClient:
        client = Mock(spec=secretmanager.SecretManagerServiceClient)
        payload = Mock(spec=['data'])
        payload.data = b'memorystore-auth-token'
        response = Mock(spec=['payload'])
        response.payload = payload
        client.access_secret_version.return_value = response
        return cast(secretmanager.SecretManagerServiceClient, client)

    @pytest.fixture
    def redis_client(self) -> redis.Redis:
        """Mock a Redis pipeline-compatible client."""
        client = MagicMock(spec=redis.client.Pipeline)
        client.connection_pool = MagicMock(
            spec=redis.ConnectionPool,
            connection_kwargs={'host': 'redis.test', 'port': 6379, 'db': 0},
        )
        client.ping.return_value = True
        client.pipeline.return_value = client
        client.__enter__.return_value = client
        client.__exit__.return_value = None

        return cast(redis.Redis, client)

    @pytest.fixture(autouse=True)
    def setup(
        self,
        monkeypatch: MonkeyPatch,
        blob: storage.Blob,
        bucket: storage.Bucket,
        storage_client: storage.Client,
        secrets_client: secretmanager.SecretManagerServiceClient,
        redis_client: redis.Redis,
    ) -> None:
        monkeypatch.setenv(ENV.GCP.PROJECT_ID, 'my-project')
        monkeypatch.setenv(ENV.GCP.CONFIG_GCS_BUCKET, 'config-bucket')
        monkeypatch.setenv(ENV.GCP.CONFIG_GCS_OBJECT, 'backend-config.json')
        monkeypatch.setenv(ENV.GCP.MEMORYSTORE_HOST, '10.0.0.5')
        monkeypatch.setenv(ENV.GCP.MEMORYSTORE_PORT, '6379')
        monkeypatch.setenv(ENV.GCP.MEMORYSTORE_AUTH_SECRET, 'my-secret-id')

        self.blob = blob
        self.bucket = bucket
        self.storage_client = storage_client
        self.secrets_client = secrets_client
        self.redis_client = redis_client

        monkeypatch.setattr(
            'cloudshortener.cloud.gcp.dao.cache.mixins.redis.Redis',
            lambda **kwargs: redis_client,
        )
        monkeypatch.setattr(
            'cloudshortener.cloud.gcp.dao.cache.mixins.secretmanager.SecretManagerServiceClient',
            lambda: secrets_client,
        )

    def test_pull_from_gcs_and_warm_cache(self, config_document: BackendConfig) -> None:
        expected_document_json = json.dumps(config_document, separators=(',', ':'), ensure_ascii=False)

        dao = GCPBackendConfigCacheDAO(prefix='app:dev', storage_client=self.storage_client)
        version = dao.version(force=True)

        assert version == 3

        self.secrets_client.access_secret_version.assert_called_once_with(
            request={'name': 'projects/my-project/secrets/my-secret-id/versions/latest'}
        )
        self.storage_client.bucket.assert_called_once_with('config-bucket')
        self.bucket.blob.assert_called_once_with('backend-config.json')

        self.redis_client.set.assert_has_calls(
            [
                call('cache:app:dev:appconfig:v3', expected_document_json, ex=CacheTTL.COOL),
                call('cache:app:dev:appconfig:v3:metadata', ANY, ex=CacheTTL.COOL),
                call('cache:app:dev:appconfig:latest', expected_document_json, ex=CacheTTL.COOL),
                call('cache:app:dev:appconfig:latest:metadata', ANY, ex=CacheTTL.COOL),
            ]
        )
        self.redis_client.execute.assert_called_once_with()

    def test_pull_with_invalid_config_json(self) -> None:
        self.blob.download_as_text.return_value = '{invalid-json'

        dao = GCPBackendConfigCacheDAO(prefix='app:dev', storage_client=self.storage_client)

        with pytest.raises(BadConfigurationError):
            dao.version(force=True)

    def test_pull_with_missing_build_field(self) -> None:
        self.blob.download_as_text.return_value = json.dumps(
            {
                'active_backend': 'redis',
                'configs': {'redirect_url': {'redis': {'host': 'h', 'port': 6379, 'db': 0}}},
            }
        )

        dao = GCPBackendConfigCacheDAO(prefix='app:dev', storage_client=self.storage_client)

        with pytest.raises(BadConfigurationError):
            dao.version(force=True)

    @pytest.mark.parametrize('build', ['not-a-version', {'version': 3}, []])
    def test_pull_with_non_int_build_field(self, build) -> None:
        self.blob.download_as_text.return_value = json.dumps(
            {
                'build': build,
                'active_backend': 'redis',
                'configs': {'redirect_url': {'redis': {'host': 'h', 'port': 6379, 'db': 0}}},
            }
        )

        dao = GCPBackendConfigCacheDAO(prefix='app:dev', storage_client=self.storage_client)

        with pytest.raises(BadConfigurationError):
            dao.version(force=True)
