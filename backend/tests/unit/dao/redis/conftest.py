from unittest.mock import MagicMock

import pytest
import redis


@pytest.fixture
def app_prefix() -> str:
    return 'testapp:test'


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
    return client
