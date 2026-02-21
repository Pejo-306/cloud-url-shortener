import re
from unittest.mock import MagicMock

import pytest
import redis

from cloudshortener.dao.redis import RedisKeySchema, UserRedisDAO
from cloudshortener.dao.exceptions import UserDoesNotExistError
from cloudshortener.constants import TTL


class TestUserRedisDAO:
    app_prefix: str
    key_schema: RedisKeySchema
    dao: UserRedisDAO
    redis_client: redis.Redis

    @pytest.fixture
    def key_schema(self) -> RedisKeySchema:
        mock = MagicMock(spec=RedisKeySchema)
        mock.user_quota_key.return_value = 'testapp:test:users:user123:quota:4000-11'
        return mock

    @pytest.fixture
    def dao(self, redis_client: redis.Redis, key_schema: RedisKeySchema, app_prefix: str) -> UserRedisDAO:
        dao = UserRedisDAO(redis_client=redis_client, prefix=app_prefix)
        dao.keys = key_schema
        return dao

    @pytest.fixture(autouse=True)
    def setup(self, dao: UserRedisDAO, redis_client: redis.Redis):
        self.dao = dao
        self.redis_client = redis_client

    def test_quota(self):
        self.redis_client.incrby.return_value = 20
        user_id = 'user123'

        quota = self.dao.quota(user_id)

        assert quota == 20
        self.redis_client.incrby.assert_called_once_with('testapp:test:users:user123:quota:4000-11', 0)
        self.redis_client.expire.assert_not_called()

    def test_increment_quota(self):
        self.redis_client.exists.return_value = 1  # key exists
        self.redis_client.incr.return_value = 21
        user_id = 'user123'

        quota = self.dao.increment_quota(user_id)

        assert quota == 21
        self.redis_client.exists.assert_called_once_with('testapp:test:users:user123:quota:4000-11')
        self.redis_client.incr.assert_called_once_with('testapp:test:users:user123:quota:4000-11')

    def test_increment_quota_user_does_not_exist(self):
        self.redis_client.exists.return_value = 0  # key does not exist
        user_id = 'user123'
        with pytest.raises(UserDoesNotExistError, match=re.escape("User with ID 'user123' does not exist.")):
            self.dao.increment_quota(user_id)

    def test_quota_auto_initialize(self):
        self.redis_client.incrby.return_value = 0
        self.redis_client.expire.return_value = 1
        user_id = 'user123'

        quota = self.dao.quota(user_id)

        assert quota == 0
        self.redis_client.incrby.assert_called_once_with('testapp:test:users:user123:quota:4000-11', 0)
        self.redis_client.expire.assert_called_once_with('testapp:test:users:user123:quota:4000-11', TTL.ONE_MONTH)
