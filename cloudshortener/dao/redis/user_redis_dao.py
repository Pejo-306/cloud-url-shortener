from typing import Optional

import redis
from beartype import beartype

from cloudshortener.dao.base import UserBaseDAO
from cloudshortener.dao.redis import RedisKeySchema
from cloudshortener.dao.redis.helpers import handle_redis_connection_error
from cloudshortener.dao.exceptions import DataStoreError, UserDoesNotExistError 
from cloudshortener.utils.constants import ONE_MONTH_SECONDS


class UserRedisDAO(UserBaseDAO):
    def __init__(self, 
                 redis_host: Optional[str] = 'localhost',
                 redis_port: Optional[int] = 6379,
                 redis_db: Optional[int] = 0,
                 redis_decode_responses: Optional[bool] = True,
                 redis_username: Optional[str] = None,
                 redis_password: Optional[str] = None,
                 redis_client: Optional[redis.Redis] = None,
                 prefix: Optional[str] = None):
        if redis_client is None:
            redis_client = redis.Redis(
                host=redis_host,
                port=redis_port,
                db=redis_db,
                decode_responses=redis_decode_responses,
                username=redis_username,
                password=redis_password
            )

        self.redis = redis_client
        self.keys = RedisKeySchema(prefix=prefix)

        self._heatlhcheck()

    @handle_redis_connection_error
    @beartype
    def quota(self, user_id: str, **kwargs) -> int:
        user_quota_key = self.keys.user_quota_key(user_id)
        monthly_quota = self.redis.incrby(user_quota_key, 0)  # Get current user quota, auto-intialize to 0
        if monthly_quota == 0:  # If user quota was just initialized, set expiration time
            self.redis.expire(user_quota_key, ONE_MONTH_SECONDS)
        return monthly_quota

    @handle_redis_connection_error
    @beartype
    def increment_quota(self, user_id, **kwargs) -> int:
        user_quota_key = self.keys.user_quota_key(user_id)
        if not self.redis.exists(user_quota_key):
            raise UserDoesNotExistError(f"User with ID '{user_id}' does not exist.")
        return self.redis.incr(user_quota_key)

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
            >>> dao._heatlhcheck()
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
                raise DataStoreError(f"Can't connect to Redis at {redis_host}:{redis_port}/{redis_db}. Check the provided configuration paramters.") from e
            return False
        else:
            return True
