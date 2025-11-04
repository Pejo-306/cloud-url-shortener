import re
from unittest.mock import MagicMock

import pytest
import redis
import redis.client

from cloudshortener.dao.redis import RedisKeySchema, UserRedisDAO
from cloudshortener.dao.exceptions import UserDoesNotExistError


@pytest.fixture
def app_prefix():
    """Provide a consistent Redis key prefix for testing."""
    return 'testapp:test'


@pytest.fixture
def redis_client():
    """Mock a Redis pipeline-compatible client."""
    _redis_client = MagicMock(spec=redis.client.Pipeline)
    _redis_client.exists.return_value = False
    _redis_client.pipeline.return_value = _redis_client
    _redis_client.__enter__.return_value = _redis_client
    _redis_client.__exit__.return_value = None
    return _redis_client


@pytest.fixture
def key_schema():
    """Mock RedisKeySchema to return predictable key values."""
    mock = MagicMock(spec=RedisKeySchema)
    mock.user_quota_key.return_value = 'testapp:test:users:user123:quota:4000-11'
    return mock


@pytest.fixture
def dao(redis_client, key_schema, app_prefix):
    """Create a ShortURLRedisDAO instance with mocked dependencies."""
    _dao = UserRedisDAO(redis_client=redis_client, prefix=app_prefix)
    _dao.keys = key_schema
    return _dao


def test_quota(dao, redis_client):
    redis_client.get.return_value = 20
    user_id = 'user123'

    quota = dao.quota(user_id)

    assert quota == 20
    redis_client.get.assert_called_once_with('testapp:test:users:user123:quota:4000-11')


def test_quota_user_does_not_exist(dao, redis_client):
    redis_client.get.return_value = None
    user_id = 'user123'
    with pytest.raises(UserDoesNotExistError, match=re.escape(f"User with ID 'user123' does not exist.")):
        dao.quota(user_id)


def test_increment_quota(dao, redis_client):
    redis_client.exists.return_value = 1  # key exists
    redis_client.incr.return_value = 21
    user_id = 'user123'

    quota = dao.increment_quota(user_id)

    assert quota == 21
    redis_client.exists.assert_called_once_with('testapp:test:users:user123:quota:4000-11')
    redis_client.incr.assert_called_once_with('testapp:test:users:user123:quota:4000-11')


def test_increment_quota_user_does_not_exist(dao, redis_client):
    redis_client.exists.return_value = 0  # key does not exists
    user_id = 'user123'
    with pytest.raises(UserDoesNotExistError, match=re.escape(f"User with ID 'user123' does not exist.")):
        dao.increment_quota(user_id)
