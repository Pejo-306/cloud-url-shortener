"""Unit tests for the ShortURLRedisDAO

Test coverage includes:

1. Initialization and configuration
   - Ensures correct initialization with or without a Redis client.
   - Confirms invalid Redis configuration raises DataStoreError.

2. Insertion behavior
   - Validates inserting valid short URLs stores both URL and hit counter.
   - Ensures invalid types raise TypeError or BeartypeCallHintParamViolation.
   - Confirms duplicate shortcodes raise ShortURLAlreadyExistsError.
   - Confirms Redis connection errors raise DataStoreError.

3. Retrieval behavior
   - Ensures fetching valid shortcodes returns a populated ShortURLModel.
   - Validates invalid parameter types raise type errors.
   - Confirms missing keys raise ShortURLNotFoundError.
   - Confirms Redis connection errors raise DataStoreError.

4. Counter operations
   - Ensures global counter increments or retrieves correctly.
   - Confirms Redis connectivity issues raise DataStoreError.
"""

import re
from unittest.mock import MagicMock, call

import pytest
import redis
import redis.client
from beartype.roar import BeartypeCallHintParamViolation

from cloudshortener.models import ShortURLModel
from cloudshortener.dao.exceptions import DataStoreError, ShortURLAlreadyExistsError, ShortURLNotFoundError
from cloudshortener.dao.redis import RedisKeySchema, ShortURLRedisDAO
from cloudshortener.utils.constants import ONE_YEAR_SECONDS, DEFAULT_LINK_HITS_QUOTA


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
    mock.link_url_key.return_value = 'testapp:test:links:abc123:url'
    mock.link_hits_key.return_value = 'testapp:test:links:abc123:hits'
    mock.counter_key.return_value = 'testapp:test:links:counter'
    return mock


@pytest.fixture
def dao(redis_client, key_schema, app_prefix):
    """Create a ShortURLRedisDAO instance with mocked dependencies."""
    _dao = ShortURLRedisDAO(redis_client=redis_client, prefix=app_prefix)
    _dao.keys = key_schema
    return _dao


# -------------------------------
# 2. Insertion behavior
# -------------------------------


def test_insert_short_url(dao, redis_client):
    """Ensure valid short URL insertion stores URL and hits atomically."""
    expected_calls = [
        call('testapp:test:links:abc123:url'),
        call('testapp:test:links:abc123:url', 'https://example.com/test', ex=ONE_YEAR_SECONDS),
        call('testapp:test:links:abc123:hits', DEFAULT_LINK_HITS_QUOTA, ex=ONE_YEAR_SECONDS),
    ]

    short_url = ShortURLModel(target='https://example.com/test', shortcode='abc123', hits=None, expires_at=None)
    dao.insert(short_url)

    assert redis_client.exists.call_count == 1
    assert redis_client.set.call_count == 2
    redis_client.exists.assert_has_calls(expected_calls[:1], any_order=False)
    redis_client.set.assert_has_calls(expected_calls[1:], any_order=False)


def test_insert_short_url_with_invalid_type(dao):
    """Ensure inserting invalid types raises TypeError or Beartype error."""
    invalid_url = 'https://example.com/notamodel'
    with pytest.raises((TypeError, BeartypeCallHintParamViolation)):
        dao.insert(invalid_url)


def test_insert_short_url_with_redis_connection_error(dao, redis_client):
    """Ensure Redis connection errors during insert raise DataStoreError."""
    short_url = ShortURLModel(target='https://example.com/failure', shortcode='abc123', expires_at=None)

    redis_client.set.side_effect = redis.exceptions.ConnectionError('Connection error')
    redis_client.connection_pool = MagicMock()
    redis_client.connection_pool.connection_kwargs = {'host': '203.0.113.1', 'port': 18000, 'db': 5}

    with pytest.raises(DataStoreError, match="Can't connect to Redis at 203.0.113.1:18000/5."):
        dao.insert(short_url)


def test_insert_short_url_which_already_exists(dao, redis_client):
    """Ensure duplicate shortcodes raise ShortURLAlreadyExistsError."""
    exception_message = "Short URL with code 'abc123' already exists."
    short_url = ShortURLModel(target='https://example.com/duplicate', shortcode='abc123', expires_at=None)

    redis_client.exists.return_value = True
    with pytest.raises(ShortURLAlreadyExistsError, match=re.escape(exception_message)):
        dao.insert(short_url)


# -------------------------------
# 3. Retrieval behavior
# -------------------------------


def test_get_short_url(dao, redis_client):
    """Ensure valid shortcode retrieval returns a complete ShortURLModel."""
    redis_client.execute.return_value = ('https://example.com/test', 10000, ONE_YEAR_SECONDS)

    short_url = dao.get('abc123')
    assert isinstance(short_url, ShortURLModel)
    assert short_url.target == 'https://example.com/test'
    assert short_url.shortcode == 'abc123'
    assert short_url.hits == 10000
    assert short_url.expires_at is not None


def test_get_short_url_with_invalid_type(dao):
    """Ensure invalid shortcode types raise TypeError or Beartype error."""
    invalid_shortcode = 12345
    with pytest.raises((TypeError, BeartypeCallHintParamViolation)):
        dao.get(invalid_shortcode)


def test_get_short_url_with_redis_connection_error(dao, redis_client):
    """Ensure Redis connection errors during get raise DataStoreError."""
    redis_client.get.side_effect = redis.exceptions.ConnectionError('Connection Error')
    redis_client.connection_pool = MagicMock()
    redis_client.connection_pool.connection_kwargs = {'host': '203.0.113.1', 'port': 18000, 'db': 5}

    with pytest.raises(DataStoreError, match="Can't connect to Redis at 203.0.113.1:18000/5."):
        dao.get('abc123')


def test_get_short_url_which_does_not_exist(dao, redis_client):
    """Ensure missing shortcodes raise ShortURLNotFoundError."""
    redis_client.execute.return_value = (None, None, -2)
    with pytest.raises(ShortURLNotFoundError, match="Short URL with code 'abc123' not found"):
        dao.get('abc123')


# -------------------------------
# 4. Counter operations
# -------------------------------


def test_count_with_increment(dao, redis_client):
    """Ensure count(increment=True) increments the global counter."""
    redis_client.incr.return_value = 43
    assert dao.count(increment=True) == 43
    redis_client.incr.assert_called_once_with('testapp:test:links:counter')
    redis_client.get.assert_not_called()


def test_count_without_increment(dao, redis_client):
    """Ensure count(increment=False) retrieves the global counter."""
    redis_client.get.return_value = 42
    assert dao.count(increment=False) == 42
    redis_client.get.assert_called_once_with('testapp:test:links:counter')
    redis_client.incr.assert_not_called()


def test_count_with_redis_connection_error(dao, redis_client):
    """Ensure Redis connection errors during count raise DataStoreError."""
    redis_client.get.side_effect = redis.exceptions.ConnectionError('Connection Error')
    redis_client.connection_pool = MagicMock()
    redis_client.connection_pool.connection_kwargs = {'host': '203.0.113.1', 'port': 18000, 'db': 5}

    with pytest.raises(DataStoreError, match="Can't connect to Redis at 203.0.113.1:18000/5."):
        dao.count(increment=False)
