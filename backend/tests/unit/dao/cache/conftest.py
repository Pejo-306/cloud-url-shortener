from unittest.mock import MagicMock

import pytest
import redis
from pytest import MonkeyPatch

from cloudshortener.utils.constants import (
    ELASTICACHE_HOST_PARAM_ENV,
    ELASTICACHE_PORT_PARAM_ENV,
    ELASTICACHE_DB_PARAM_ENV,
    ELASTICACHE_USER_PARAM_ENV,
    ELASTICACHE_SECRET_ENV,
)


@pytest.fixture
def app_prefix() -> str:
    return 'testapp:test'


@pytest.fixture(autouse=True)
def _env(monkeypatch: MonkeyPatch) -> None:
    monkeypatch.setenv(ELASTICACHE_HOST_PARAM_ENV, '/test/elasticache/host')
    monkeypatch.setenv(ELASTICACHE_PORT_PARAM_ENV, '/test/elasticache/port')
    monkeypatch.setenv(ELASTICACHE_DB_PARAM_ENV, '/test/elasticache/db')
    monkeypatch.setenv(ELASTICACHE_USER_PARAM_ENV, '/test/elasticache/user')
    monkeypatch.setenv(ELASTICACHE_SECRET_ENV, 'test/elasticache/credentials')


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