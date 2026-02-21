import re
from datetime import datetime, UTC
from unittest.mock import MagicMock, call

import pytest
import redis
from freezegun import freeze_time

from cloudshortener.models import ShortURLModel
from cloudshortener.dao.exceptions import ShortURLAlreadyExistsError, ShortURLNotFoundError
from cloudshortener.dao.redis import RedisKeySchema, ShortURLRedisDAO
from cloudshortener.constants import TTL, DefaultQuota


class TestShortURLRedisDAO:
    app_prefix: str
    key_schema: RedisKeySchema
    dao: ShortURLRedisDAO
    redis_client: redis.Redis

    @pytest.fixture
    def key_schema(self) -> RedisKeySchema:
        mock = MagicMock(spec=RedisKeySchema)
        mock.link_url_key.return_value = 'testapp:test:links:abc123:url'
        mock.link_hits_key.return_value = 'testapp:test:links:abc123:hits:2025-10'
        mock.counter_key.return_value = 'testapp:test:links:counter'
        return mock

    @pytest.fixture
    def dao(self, redis_client: redis.Redis, key_schema: RedisKeySchema, app_prefix: str) -> ShortURLRedisDAO:
        dao = ShortURLRedisDAO(redis_client=redis_client, prefix=app_prefix)
        dao.keys = key_schema
        return dao

    @pytest.fixture(autouse=True)
    def setup(self, dao: ShortURLRedisDAO, redis_client: redis.Redis):
        self.dao = dao
        self.redis_client = redis_client

    @freeze_time('2025-10-15')
    def test_insert_short_url(self):
        first_moment_of_next_month_ts = int(datetime.strptime('2025-11-01 00:00:00', '%Y-%m-%d %H:%M:%S').replace(tzinfo=UTC).timestamp())
        expected_calls = [
            call('testapp:test:links:abc123:url'),
            call('testapp:test:links:abc123:url', 'https://example.com/test', ex=TTL.ONE_YEAR),
            call('testapp:test:links:abc123:hits:2025-10', DefaultQuota.LINK_HITS, nx=True, exat=first_moment_of_next_month_ts),
        ]

        short_url = ShortURLModel(target='https://example.com/test', shortcode='abc123')
        self.dao.insert(short_url)

        assert self.redis_client.exists.call_count == 1
        assert self.redis_client.set.call_count == 2
        self.redis_client.exists.assert_has_calls(expected_calls[:1], any_order=False)
        self.redis_client.set.assert_has_calls(expected_calls[1:], any_order=False)

    def test_insert_short_url_which_already_exists(self):
        exception_message = "Short URL with code 'abc123' already exists."
        short_url = ShortURLModel(target='https://example.com/duplicate', shortcode='abc123')

        self.redis_client.exists.return_value = True
        with pytest.raises(ShortURLAlreadyExistsError, match=re.escape(exception_message)):
            self.dao.insert(short_url)

    @freeze_time('2025-10-15')
    def test_get_short_url(self):
        self.redis_client.execute.return_value = ('https://example.com/test', 10000, TTL.ONE_YEAR)

        short_url = self.dao.get('abc123')
        assert isinstance(short_url, ShortURLModel)
        assert short_url.target == 'https://example.com/test'
        assert short_url.shortcode == 'abc123'
        assert short_url.hits == 10000
        assert short_url.expires_at == datetime(2026, 10, 15, 0, 0, 0, tzinfo=UTC)

    def test_get_short_url_which_does_not_exist(self):
        self.redis_client.execute.return_value = (None, None, -2)
        with pytest.raises(ShortURLNotFoundError, match="Short URL with code 'abc123' not found."):
            self.dao.get('abc123')

    def test_count_with_increment(self):
        self.redis_client.incr.return_value = 43
        assert self.dao.count(increment=True) == 43
        self.redis_client.incr.assert_called_once_with('testapp:test:links:counter')
        self.redis_client.get.assert_not_called()

    def test_count_without_increment(self):
        self.redis_client.get.return_value = 42
        assert self.dao.count(increment=False) == 42
        self.redis_client.get.assert_called_once_with('testapp:test:links:counter')
        self.redis_client.incr.assert_not_called()

    @freeze_time('2025-10-15')
    def test_hit_decrements_existing_monthly_quota(self):
        self.redis_client.exists.side_effect = lambda key: key == 'testapp:test:links:abc123:url'
        # fmt: off
        self.redis_client.execute.return_value = (
            None,
            9994
        )
        # fmt: on

        result = self.dao.hit('abc123')

        assert result == 9994
        self.redis_client.exists.assert_called_once_with('testapp:test:links:abc123:url')
        self.redis_client.decr.assert_called_once_with('testapp:test:links:abc123:hits:2025-10')

    @freeze_time('2025-10-15')
    def test_hit_initializes_monthly_quota_when_missing(self):
        self.redis_client.exists.side_effect = lambda key: key == 'testapp:test:links:abc123:url'
        # fmt: off
        self.redis_client.execute.return_value = (
            True,
            DefaultQuota.LINK_HITS - 1
        )
        # fmt: on

        expire_at = int(datetime(2025, 11, 1, 0, 0, 0, tzinfo=UTC).timestamp())

        result = self.dao.hit('abc123')

        assert result == DefaultQuota.LINK_HITS - 1
        self.redis_client.exists.assert_called_once_with('testapp:test:links:abc123:url')
        self.redis_client.set.assert_called_once_with(
            'testapp:test:links:abc123:hits:2025-10',
            DefaultQuota.LINK_HITS,
            nx=True,
            exat=expire_at,
        )
        self.redis_client.decr.assert_called_once_with('testapp:test:links:abc123:hits:2025-10')

    @freeze_time('2025-10-15')
    def test_hit_raises_error_when_link_does_not_exist(self):
        self.redis_client.exists.return_value = False

        with pytest.raises(ShortURLNotFoundError, match="Short URL with code 'abc123' not found"):
            self.dao.hit('abc123')

        self.redis_client.exists.assert_called_once_with('testapp:test:links:abc123:url')
        self.redis_client.decr.assert_not_called()

    @freeze_time('2025-10-15')
    def test_hit_allows_negative_values(self):
        self.redis_client.exists.side_effect = lambda key: key == 'testapp:test:links:abc123:url'
        self.redis_client.execute.return_value = (
            None,
            -233,
        )

        result = self.dao.hit('abc123')

        assert result == -233
        self.redis_client.decr.assert_called_once_with('testapp:test:links:abc123:hits:2025-10')
