from typing import Optional

import redis

from cloudshortener.dao.redis import RedisKeySchema
from cloudshortener.dao.exceptions import DataStoreError


class RedisClientMixin:
    """Mixin Redis client setup and health check for Redis-backed DAOs.

    You can provide either raw connection parameters or a pre-initialized Redis client instance.

    Public Attributes:
        redis (redis.Redis):
            Active Redis client instance used by subclasses.

        keys (RedisKeySchema):
            Helper class for generating namespaced Redis key names.
    """

    # TODO: change these type hints from Optional to type | None
    def __init__(
        self,
        redis_host: Optional[str] = 'localhost',
        redis_port: Optional[int] = 6379,
        redis_db: Optional[int] = 0,
        redis_decode_responses: Optional[bool] = True,
        redis_username: Optional[str] = None,
        redis_password: Optional[str] = None,
        redis_client: Optional[redis.Redis] = None,
        prefix: Optional[str] = None,
    ):
        if redis_client is None:
            redis_client = redis.Redis(
                host=redis_host,
                port=int(redis_port),
                db=int(redis_db),
                decode_responses=redis_decode_responses,
                username=redis_username,
                password=redis_password,
            )

        self.redis = redis_client
        self.keys = RedisKeySchema(prefix=prefix)

        self._heatlhcheck()

    def _heatlhcheck(self, raise_error: bool = True) -> bool:
        try:
            self.redis.ping()
        except redis.exceptions.ConnectionError as e:
            if raise_error:
                info = self.redis.connection_pool.connection_kwargs
                redis_host = info.get('host')
                redis_port = info.get('port')
                redis_db = info.get('db')
                raise DataStoreError(
                    f"Can't connect to Redis at {redis_host}:{redis_port}/{redis_db}. Check the provided configuration paramters."
                ) from e
            return False  # pragma: no cover
        else:
            return True
