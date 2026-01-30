import pytest
import redis

from cloudshortener.dao.redis.helpers import handle_redis_connection_error
from cloudshortener.dao.exceptions import DataStoreError


def test_handle_redis_connection_error(redis_client: redis.Redis):
    class DummyDAO:
        def __init__(self):
            self.redis = redis_client

        @handle_redis_connection_error
        def fail(self):
            raise redis.exceptions.ConnectionError('Cannot connect')

    dao = DummyDAO()

    with pytest.raises(DataStoreError, match="Can't connect to Redis at redis.test:6379/0."):
        dao.fail()
