"""Unit tests for Redis-based mixins.

Test coverage includes:
    1. Initialization and configuration
       - Ensures correct initialization with or without a Redis client.
       - Confirms invalid Redis configuration raises DataStoreError.
    2. Healthcheck behavior
       - Healthcheck pings Redis.
       - Missed pong from Redis raises error.
"""

from unittest.mock import MagicMock, patch

import pytest
import redis

from cloudshortener.dao.exceptions import DataStoreError
from cloudshortener.dao.redis.mixins import RedisClientMixin


# -------------------------------
# Fixtures
# -------------------------------


@pytest.fixture
def redis_client():
    _redis_client = MagicMock(
        spec=redis.Redis, connection_pool=MagicMock(spec=redis.ConnectionPool, connection_kwargs={'host': 'redis', 'port': 6379, 'db': 0})
    )
    _redis_client.ping.return_value = True
    return _redis_client


# -------------------------------
# 1. Initialization and configuration
# -------------------------------


def test_initialize_without_redis_client():
    """Ensure DAO creates a Redis client when none is provided."""
    redis_config = {
        'redis_host': 'redis',
        'redis_port': 6379,
        'redis_db': 0,
        'redis_decode_responses': True,
        'redis_username': 'default',
        'redis_password': 'password',
    }

    with patch('cloudshortener.dao.redis.mixins.redis.Redis', autospec=True) as redis_mock:
        redis_mock_instance = redis_mock.return_value
        mixin = RedisClientMixin(**redis_config, prefix='testapp:test')

        redis_mock.assert_called_once_with(host='redis', port=6379, db=0, decode_responses=True, username='default', password='password')
        assert mixin.redis is redis_mock_instance


def test_initialize_with_redis_client():
    """Ensure DAO correctly uses a pre-initialized Redis client."""
    redis_mock = MagicMock(spec=redis.Redis)
    mixin = RedisClientMixin(redis_client=redis_mock, prefix='testapp:test')
    assert mixin.redis is redis_mock


def test_initialize_with_invalid_redis_config():
    """Ensure invalid Redis config raises DataStoreError."""
    redis_config = {
        'redis_host': '203.0.113.1',
        'redis_port': 18000,
        'redis_db': 5,
        'redis_decode_responses': True,
        'redis_username': 'default',
        'redis_password': 'password',
    }
    exception_message = "Can't connect to Redis at 203.0.113.1:18000/5. Check the provided configuration paramters."

    with patch('cloudshortener.dao.redis.mixins.redis.Redis', autospec=True) as redis_mock:
        redis_mock_instance = redis_mock.return_value
        redis_mock_instance.ping.side_effect = redis.exceptions.ConnectionError('Connection error')
        redis_mock_instance.connection_pool = MagicMock()
        redis_mock_instance.connection_pool.connection_kwargs = {'host': '203.0.113.1', 'port': 18000, 'db': 5}

        with pytest.raises(DataStoreError, match=exception_message):
            RedisClientMixin(**redis_config, prefix='testapp:test')


# -------------------------------
# 2. Healthcheck behavior
# -------------------------------
def test_healthcheck_passes(redis_client):
    """Ensure healthcheck passes when Redis responds."""
    mixin = RedisClientMixin(redis_client=redis_client, prefix='testapp:test')
    redis_client.ping.assert_called_once()  # initialization performs a healthcheck

    pong = mixin._heatlhcheck()

    assert pong
    redis_client.ping.call_count == 2  # once in intialization, once separately


def test_healthcheck_fails(redis_client):
    """Ensure healthcheck raises DataStoreError when Redis is unreachable."""
    redis_client.ping.side_effect = redis.exceptions.ConnectionError('Connection error')

    with pytest.raises(DataStoreError):
        RedisClientMixin(redis_client=redis_client, prefix='testapp:test')
