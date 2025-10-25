from unittest.mock import MagicMock, call

import redis
import pytest

from cloudshortener.models import ShortURLModel
from cloudshortener.dao.redis import RedisKeySchema, ShortURLRedisDAO


ONE_YEAR_SECONDS = 31_536_000

# How does ShortURLRedisDAO interact with Redis?
# 1- insert(ShortURLModel) -> SET 2 keys
# 2- get(short_code) -> GET 2 keys

@pytest.fixture
def app_prefix():
    return 'testapp:test'


@pytest.fixture
def redis_client():
    return MagicMock(spec=redis.Redis)


@pytest.fixture
def key_schema():
    mock = MagicMock(spec=RedisKeySchema)
    mock.link_url_key.return_value = 'testapp:test:links:abc123:url'
    mock.link_hits_key.return_value = 'testapp:test:links:abc123:hits'
    return mock


@pytest.fixture
def dao(redis_client, key_schema, app_prefix):
    _dao = ShortURLRedisDAO(redis_client=redis_client, prefix=app_prefix)
    _dao.keys = key_schema
    return _dao


def test_insert_short_url(dao, redis_client):
    expected_calls = [
        call('testapp:test:links:abc123:url', 'https://example.com/test', ex=ONE_YEAR_SECONDS),
        call('testapp:test:links:abc123:hits', 10000, ex=ONE_YEAR_SECONDS),
    ]

    short_url = ShortURLModel(
        short_code='abc123',
        original_url='https://example.com/test',
        expires_at=None
    )
    dao.insert(short_url)

    assert redis_client.set.call_count == 2
    redis_client.set.assert_has_calls(expected_calls, any_order=False)


def test_get_short_url(dao, redis_client):
    redis_client.get.side_effect = [
        b'https://example.com/test',
        b'10000'
    ]
    redis_client.ttl.return_value = str(ONE_YEAR_SECONDS).encode('utf-8')
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
    assert short_url.short_code == 'abc123'
    assert short_url.original_url == 'https://example.com/test'
    assert short_url.expires_at is not None

