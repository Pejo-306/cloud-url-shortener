"""
Unit tests for the UserRedisDAO class.

Verify that user quota operations correctly interact with Redis and handle
missing user scenarios with appropriate exceptions.

Test coverage includes:

1. Retrieving user quotas
   - Ensures `quota()` returns the correct stored value for an existing user.

2. Incrementing user quotas
   - Ensures `increment_quota()` increments and returns the updated value when the key exists.

3. Missing user
   - Ensures  `increment_quota()` raise UserDoesNotExistError when
     the user record does not exist.

4. Auto-initialize user quota
   - Ensure `quota()` auto initializes a user's monthly quota to 0 if key does not exist in Redis.

Fixtures:
    - `app_prefix`: consistent Redis key prefix for predictable test output.
    - `redis_client`: mock Redis pipeline-compatible client.
    - `key_schema`: mock RedisKeySchema generating static key names.
    - `dao`: instance of UserRedisDAO with mocked Redis and key schema dependencies.
"""

import re
from unittest.mock import MagicMock

import pytest
import redis.client

from cloudshortener.dao.redis import RedisKeySchema, UserRedisDAO
from cloudshortener.dao.exceptions import UserDoesNotExistError
from cloudshortener.utils.constants import ONE_MONTH_SECONDS


# -------------------------------
# Fixtures
# -------------------------------


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
    """Create a UserRedisDAO instance with mocked dependencies."""
    _dao = UserRedisDAO(redis_client=redis_client, prefix=app_prefix)
    _dao.keys = key_schema
    return _dao


# -------------------------------
# 1. Retrieving user quotas
# -------------------------------


def test_quota(dao, redis_client):
    """Ensure `quota()` returns correct value for an existing user."""
    redis_client.incrby.return_value = 20
    user_id = 'user123'

    quota = dao.quota(user_id)

    assert quota == 20
    redis_client.incrby.assert_called_once_with('testapp:test:users:user123:quota:4000-11', 0)
    redis_client.expire.assert_not_called()


# -------------------------------
# 2. Incrementing user quotas
# -------------------------------


def test_increment_quota(dao, redis_client):
    """Ensure `increment_quota()` increments and returns new value when key exists."""
    redis_client.exists.return_value = 1  # key exists
    redis_client.incr.return_value = 21
    user_id = 'user123'

    quota = dao.increment_quota(user_id)

    assert quota == 21
    redis_client.exists.assert_called_once_with('testapp:test:users:user123:quota:4000-11')
    redis_client.incr.assert_called_once_with('testapp:test:users:user123:quota:4000-11')


# -------------------------------
# 3. Missing user
# -------------------------------


def test_increment_quota_user_does_not_exist(dao, redis_client):
    """Ensure `increment_quota()` raises UserDoesNotExistError when user is missing."""
    redis_client.exists.return_value = 0  # key does not exist
    user_id = 'user123'
    with pytest.raises(UserDoesNotExistError, match=re.escape("User with ID 'user123' does not exist.")):
        dao.increment_quota(user_id)


# -------------------------------
# 4. Auto-initialize user quota
# -------------------------------


def test_quota_auto_initialize(dao, redis_client):
    """Ensure `quota()` auto-initializes user quota when missing."""
    redis_client.incrby.return_value = 0
    redis_client.expire.return_value = 1
    user_id = 'user123'

    quota = dao.quota(user_id)

    assert quota == 0
    redis_client.incrby.assert_called_once_with('testapp:test:users:user123:quota:4000-11', 0)
    redis_client.expire.assert_called_once_with('testapp:test:users:user123:quota:4000-11', ONE_MONTH_SECONDS)
