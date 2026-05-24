from unittest.mock import Mock

import pytest
import redis
from google.cloud import secretmanager
from pytest import MonkeyPatch

from cloudshortener.cloud.dao.cache import CacheKeySchema
from cloudshortener.cloud.gcp.dao.cache.mixins import MemoryStoreClientMixin
from cloudshortener.constants import ENV
from cloudshortener.exceptions import BadConfigurationError, MalformedResponseError


class ConcreteMemoryStoreMixin(MemoryStoreClientMixin):
    """Concrete subclass for testing the mixin in isolation."""


class TestMemoryStoreClientMixin:
    @pytest.fixture(autouse=True)
    def env(self, monkeypatch: MonkeyPatch) -> None:
        monkeypatch.setenv(ENV.GCP.GCP_PROJECT_ID, 'my-project')
        monkeypatch.setenv(ENV.GCP.MEMORYSTORE_HOST, '10.0.0.5')
        monkeypatch.setenv(ENV.GCP.MEMORYSTORE_PORT, '6379')
        monkeypatch.setenv(ENV.GCP.MEMORYSTORE_AUTH_SECRET, 'my-secret-id')

    @pytest.fixture
    def secrets_client(self) -> Mock:
        client = Mock(spec=secretmanager.SecretManagerServiceClient)
        payload = Mock(spec=['data'])
        payload.data = b'memorystore-auth-token'
        response = Mock(spec=['payload'])
        response.payload = payload
        client.access_secret_version.return_value = response
        return client

    @pytest.fixture
    def redis_client(self) -> Mock:
        mock_redis = Mock(spec=redis.Redis)
        mock_redis.ping.return_value = True
        return mock_redis

    @pytest.fixture(autouse=True)
    def setup(self, monkeypatch: MonkeyPatch, redis_client: Mock, secrets_client: Mock) -> None:
        self.redis_client = redis_client
        self.secrets_client = secrets_client

        monkeypatch.setattr(
            'cloudshortener.cloud.gcp.dao.cache.mixins.redis.Redis',
            lambda **kwargs: redis_client,
        )

    def test_initialization_resolves_secret_and_constructs_redis_and_keys(self) -> None:
        mixin = ConcreteMemoryStoreMixin(prefix='app:dev', secrets_client=self.secrets_client)

        self.secrets_client.access_secret_version.assert_called_once_with(
            request={'name': 'projects/my-project/secrets/my-secret-id/versions/latest'}
        )
        assert mixin.redis is self.redis_client
        assert isinstance(mixin.keys, CacheKeySchema)
        assert mixin.keys.appconfig_latest_key() == 'cache:app:dev:appconfig:latest'

    @pytest.mark.parametrize('port_value', ['not-a-port', '6379.1', ''])
    def test_initialization_with_non_int_memorystore_port(self, monkeypatch: MonkeyPatch, port_value: str) -> None:
        monkeypatch.setenv(ENV.GCP.MEMORYSTORE_PORT, port_value)

        with pytest.raises(BadConfigurationError):
            ConcreteMemoryStoreMixin(prefix='app:dev', secrets_client=self.secrets_client)

    def test_initialization_with_undecodable_secret_payload(self) -> None:
        self.secrets_client.access_secret_version.return_value.payload.data = b'\xff'

        with pytest.raises(MalformedResponseError):
            ConcreteMemoryStoreMixin(prefix='app:dev', secrets_client=self.secrets_client)

    def test_initialization_with_empty_secret_payload(self) -> None:
        self.secrets_client.access_secret_version.return_value.payload.data = b''

        with pytest.raises(BadConfigurationError):
            ConcreteMemoryStoreMixin(prefix='app:dev', secrets_client=self.secrets_client)
