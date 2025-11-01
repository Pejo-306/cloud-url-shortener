import re
from unittest.mock import MagicMock, call, patch

import pytest
import redis
import redis.client
from beartype.roar import BeartypeCallHintParamViolation

from cloudshortener.models import ShortURLModel
from cloudshortener.dao.exceptions import DataStoreError, ShortURLAlreadyExistsError, ShortURLNotFoundError
from cloudshortener.dao.redis import RedisKeySchema, ShortURLRedisDAO
from cloudshortener.utils.constants import ONE_YEAR_SECONDS, DEFAULT_LINK_HITS_QUOTA


@pytest.fixture
def app_prefix():
    return 'testapp:test'


@pytest.fixture
def redis_client():
    _redis_client = MagicMock(spec=redis.client.Pipeline)
    _redis_client.exists.return_value = False
    # Transform Redis pipelines to regular Redis client for testing purposes
    _redis_client.pipeline.return_value = _redis_client
    _redis_client.__enter__.return_value = _redis_client
    _redis_client.__exit__.return_value = None
    return _redis_client


@pytest.fixture
def key_schema():
    mock = MagicMock(spec=RedisKeySchema)
    mock.link_url_key.return_value = 'testapp:test:links:abc123:url'
    mock.link_hits_key.return_value = 'testapp:test:links:abc123:hits'
    mock.counter_key.return_value = 'testapp:test:links:counter'
    return mock


@pytest.fixture
def dao(redis_client, key_schema, app_prefix):
    _dao = ShortURLRedisDAO(redis_client=redis_client, prefix=app_prefix)
    _dao.keys = key_schema
    return _dao


def test_initialize_without_redis_client():
    redis_config = {
        'redis_host': 'redis',
        'redis_port': 6379,
        'redis_db': 0,
        'redis_decode_responses': True,
        'redis_username': 'default',
        'redis_password': 'password'
    }

    with patch('cloudshortener.dao.redis.short_url_redis_dao.redis.Redis', autospec=True) as redis_mock:
        redis_mock_instance = redis_mock.return_value

        dao = ShortURLRedisDAO(**redis_config, prefix='testapp:test')

        redis_mock.assert_called_once_with(
            host='redis',
            port=6379,
            db=0,
            decode_responses=True,
            username='default',
            password='password'
        )
        assert dao.redis is redis_mock_instance


def test_initialize_with_redis_client():
    redis_mock = MagicMock(
        spec=redis.Redis,
        host='redis',
        port=6379,
        db=0,
        decode_responses=True,
    )
    dao = ShortURLRedisDAO(redis_client=redis_mock, prefix='testapp:test')

    assert dao.redis is redis_mock


def test_initialize_with_invalid_redis_config():
    redis_config = {
        'redis_host': '203.0.113.1',
        'redis_port': 18000,
        'redis_db': 5,
        'redis_decode_responses': True,
        'redis_username': 'default',
        'redis_password': 'password'
    }
    exception_message = (
        "Can't connect to Redis at 203.0.113.1:18000/5. "
        "Check the provided configuration paramters."
    )

    with patch('cloudshortener.dao.redis.short_url_redis_dao.redis.Redis', autospec=True) as redis_mock:
        redis_mock_instance = redis_mock.return_value
        redis_mock_instance.ping.side_effect = redis.exceptions.ConnectionError("Connection error")
        redis_mock_instance.connection_pool = MagicMock()
        redis_mock_instance.connection_pool.connection_kwargs = {
            'host': '203.0.113.1',
            'port': 18000,
            'db': 5
        }

        with pytest.raises(DataStoreError, match=exception_message):
            ShortURLRedisDAO(**redis_config, prefix='testapp:test')


def test_insert_short_url(dao, redis_client):
    # EXISTS <app>:links:<shortcode>:url
    # SET <app>:links:<shortcode>:url <url> EX <ttl>
    # SET <app>:links:<shortcode>:hits <monthly hits quota> EX <ttl>
    expected_calls = [
        call('testapp:test:links:abc123:url'),
        call('testapp:test:links:abc123:url', 'https://example.com/test', ex=ONE_YEAR_SECONDS),
        call('testapp:test:links:abc123:hits', DEFAULT_LINK_HITS_QUOTA, ex=ONE_YEAR_SECONDS),
    ]

    short_url = ShortURLModel(
        target='https://example.com/test',
        shortcode='abc123',
        hits=None,
        expires_at=None
    )
    dao.insert(short_url)

    assert redis_client.exists.call_count == 1
    assert redis_client.set.call_count == 2
    redis_client.exists.assert_has_calls(expected_calls[:1], any_order=False)
    redis_client.set.assert_has_calls(expected_calls[1:], any_order=False)


def test_insert_short_url_with_invalid_type(dao):
    invalid_url = 'https://example.com/notamodel'

    # Passing a plain string instead of ShortURLModel should raise TypeError
    with pytest.raises((TypeError, BeartypeCallHintParamViolation)):
        dao.insert(invalid_url)


def test_insert_short_url_with_redis_connection_error(dao, redis_client):
    short_url = ShortURLModel(
        target='https://example.com/failure',
        shortcode='abc123',
        expires_at=None
    )

    # Simulate Redis connection failure
    redis_client.set.side_effect = redis.exceptions.ConnectionError("Connection error")
    redis_client.connection_pool = MagicMock()
    redis_client.connection_pool.connection_kwargs = {
        'host': '203.0.113.1',
        'port': 18000,
        'db': 5
    }

    with pytest.raises(DataStoreError, match="Can't connect to Redis at 203.0.113.1:18000/5."):
        dao.insert(short_url)


def test_insert_short_url_which_already_exists(dao, redis_client):
    exception_message = "Short URL with code 'abc123' already exists."
    short_url = ShortURLModel(
        target='https://example.com/duplicate',
        shortcode='abc123',
        expires_at=None
    )

    # Simulate that key already exists in Redis
    redis_client.exists.return_value = True

    with pytest.raises(ShortURLAlreadyExistsError, match=re.escape(exception_message)):
        dao.insert(short_url)


def test_get_short_url(dao, redis_client):
    redis_client.execute.return_value = (
        'https://example.com/test',
        10000,
        ONE_YEAR_SECONDS
    )
    expected_calls = [
        call('testapp:test:links:abc123:url'),      # GET <app>:links:<short code>:url
        call('testapp:test:links:abc123:hits'),     # GET <app>:links:<short code>:hits
        call('testapp:test:links:abc123:url'),      # TTL <app>:links:<short code>:url
    ]

    short_url = dao.get('abc123')

    # Asset Redis Client was called with 2x GET and 1x TTL 
    assert redis_client.get.call_count == 2
    assert redis_client.ttl.call_count == 1
    redis_client.get.assert_has_calls(expected_calls[:2], any_order=False)
    redis_client.ttl.assert_has_calls(expected_calls[2:], any_order=False)

    # Assert DAO creates a valid ShortURLModel instance
    assert isinstance(short_url, ShortURLModel)
    assert short_url.target == 'https://example.com/test'
    assert short_url.shortcode == 'abc123'
    assert short_url.hits == 10000
    assert short_url.expires_at is not None


def test_get_short_url_with_invalid_type(dao):
    invalid_shortcode = 12345  # not a string

    # Accept both legacy TypeError and Beartype exception for backward compatibility
    with pytest.raises((TypeError, BeartypeCallHintParamViolation)):
        dao.get(invalid_shortcode)


def test_get_short_url_with_redis_connection_error(dao, redis_client):
    # Simulate Redis connection failure
    redis_client.get.side_effect = redis.exceptions.ConnectionError("Connection Error")
    redis_client.connection_pool = MagicMock()
    redis_client.connection_pool.connection_kwargs = {
        'host': '203.0.113.1',
        'port': 18000,
        'db': 5
    }

    # Expect DataStoreError with descriptive connection info
    with pytest.raises(DataStoreError, match="Can't connect to Redis at 203.0.113.1:18000/5."):
        dao.get('abc123')


def test_get_short_url_which_does_not_exist(dao, redis_client):
    # Simulate missing Redis keys
    redis_client.execute.return_value = (None, None, -2)

    with pytest.raises(ShortURLNotFoundError, match="Short URL with code 'abc123' not found"):
        dao.get('abc123')


def test_count_with_increment(dao, redis_client):
    redis_client.incr.return_value = 43

    assert dao.count(increment=True) == 43

    redis_client.incr.assert_called_once_with('testapp:test:links:counter')
    redis_client.get.assert_not_called()


def test_count_without_increment(dao, redis_client):
    redis_client.get.return_value = 42

    assert dao.count(increment=False) == 42

    redis_client.get.assert_called_once_with('testapp:test:links:counter')
    redis_client.incr.assert_not_called()


def test_count_with_redis_connection_error(dao, redis_client):
    # Simulate Redis connection failure
    redis_client.get.side_effect = redis.exceptions.ConnectionError("Connection Error")
    redis_client.connection_pool = MagicMock()
    redis_client.connection_pool.connection_kwargs = {
        'host': '203.0.113.1',
        'port': 18000,
        'db': 5
    }

    # Expect DataStoreError with descriptive connection info
    with pytest.raises(DataStoreError, match="Can't connect to Redis at 203.0.113.1:18000/5."):
        dao.count(increment=False)
