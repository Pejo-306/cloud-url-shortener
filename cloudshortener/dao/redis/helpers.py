import functools
import redis

from cloudshortener.dao.exceptions import DataStoreError


__all__ = []


def handle_redis_connection_error(method):
    @functools.wraps(method)
    def wrapper(self, *args, **kwargs):
        try:
            return method(self, *args, **kwargs)
        except redis.exceptions.ConnectionError as e:
            info = self.redis.connection_pool.connection_kwargs
            redis_host = info.get('host')
            redis_port = info.get('port')
            redis_db = info.get('db')
            raise DataStoreError(f"Can't connect to Redis at {redis_host}:{redis_port}/{redis_db}.") from e
    return wrapper
