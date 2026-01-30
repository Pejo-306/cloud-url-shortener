from unittest.mock import MagicMock

import pytest
import redis
from pytest import MonkeyPatch

from cloudshortener.constants import ENV


@pytest.fixture
def app_prefix() -> str:
    return 'testapp:test'


@pytest.fixture(autouse=True)
def _env(monkeypatch: MonkeyPatch) -> None:
    monkeypatch.setenv(ENV.ElastiCache.HOST_PARAM, '/test/elasticache/host')
    monkeypatch.setenv(ENV.ElastiCache.PORT_PARAM, '/test/elasticache/port')
    monkeypatch.setenv(ENV.ElastiCache.DB_PARAM, '/test/elasticache/db')
    monkeypatch.setenv(ENV.ElastiCache.USER_PARAM, '/test/elasticache/user')
    monkeypatch.setenv(ENV.ElastiCache.SECRET, 'test/elasticache/credentials')


@pytest.fixture
def redis_client() -> redis.Redis:
    """Mock a Redis pipeline-compatible client."""
    client = MagicMock(spec=redis.client.Pipeline)
    client.connection_pool = MagicMock(
        spec=redis.ConnectionPool,
        connection_kwargs={'host': 'redis.test', 'port': 6379, 'db': 0},
    )
    client.exists.return_value = False
    client.pipeline.return_value = client
    client.__enter__.return_value = client
    client.__exit__.return_value = None
    client.get.return_value = None
    return client
