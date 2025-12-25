"""Redis mixin providing shared client initialization and connectivity checks.

Responsibilities:
    - Initialized Redis client
    - Healthcheck Redis client

Classes:
    - RedisClientMixin: Base mixin to inject Redis key managemnent, client setup & healthcheck.

Example:
    Typical usage with a DAO implementation:

        >>> class UserRedisDAO(RedisClientMixin, UserBaseDAO):
        ...     pass
        ...
        >>> dao = UserRedisDAO(prefix="myapp:prod")
        >>> dao._healthcheck()
        True
"""

from typing import Optional

import redis

from cloudshortener.dao.redis import RedisKeySchema
from cloudshortener.dao.exceptions import DataStoreError


class RedisClientMixin:
    """Mixin Redis client setup and health check for Redis-backed DAOs.

    Attributes:
        redis (redis.Redis):
            Active Redis client instance used by subclasses.

        keys (RedisKeySchema):
            Helper class for generating namespaced Redis key names.

    Methods:
        _healthcheck(raise_error: bool = True) -> bool:
            Ping Redis to verify connectivity.
            Optionally raise a DataStoreError if unreachable.
    """

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
        """Initialize a Redis-based DAO for short URL management

        The option is given to either use an existing Redis client instance or
        create one via the appropriate Redis connection parameters.

        Args:
            redis_host (Optional[str]):
                Hostname of the Redis server. Defaults to 'localhost'.

            redis_port (Optional[int]):
                Redis server port. Defaults to 6379.

            redis_db (Optional[int]):
                Redis database index. Defaults to 0.

            redis_decode_responses (Optional[bool]):
                If True, decodes Redis responses. Defaults to True.

            redis_username (Optional[str]):
                Username for Redis authentication (if required).

            redis_password (Optional[str]):
                Password for Redis authentication (if required).

            redis_client (Optional[redis.Redis]):
                Pre-initialized Redis client. If None, a new client is created.

            prefix (Optional[str]):
                Namespace prefix for all Redis keys, e.g. 'app:env'.

        Raises:
            DataStoreError:
                If Redis healthcheck fails (connectivity issues).
        """
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
        """PING Redis to healthcheck connectivity

        Args:
            raise_error (bool):
                If True, raises DataStoreError on failure. Defaults to True.

        Returns:
            bool:
                True if Redis is reachable, False otherwise (only if raise_error=False).

        Raises:
            DataStoreError:
                If Redis connection cannot be established and raise_error=True.

        Example:
            >>> self._heatlhcheck()
            True
        """
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
