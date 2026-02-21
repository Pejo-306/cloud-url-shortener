import pytest
import redis

from cloudshortener.dao.exceptions import DataStoreError
from cloudshortener.dao.redis.mixins import RedisClientMixin


class TestRedisClientMixin:
    redis_client: redis.Redis
    unhealthy_redis_client: redis.Redis

    @pytest.fixture
    def unhealthy_redis_client(self, redis_client: redis.Redis) -> redis.Redis:
        redis_client.ping.side_effect = redis.exceptions.ConnectionError('Connection error')
        return redis_client

    def test_healthcheck_passes_with_healthy_redis(self, redis_client: redis.Redis):
        RedisClientMixin(redis_client=redis_client, prefix='testapp:test')
        redis_client.ping.assert_called_once()  # initialization performs a healthcheck

    def test_healthcheck_fails_with_unhealthy_redis(self, unhealthy_redis_client: redis.Redis):
        with pytest.raises(DataStoreError):
            RedisClientMixin(redis_client=unhealthy_redis_client, prefix='testapp:test')
