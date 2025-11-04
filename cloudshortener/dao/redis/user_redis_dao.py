"""Data Access Object (DAO) implementation for managing user quotas in Redis

This module provides a Redis-based implementation of UserBaseDAO for tracking
per-user monthly link generation quotas.

Responsibilities:
    - Retrieve and increment user monthly quotas;
    - Initialize user quota keys with one-month expiration;
    - Ensure data consistency and defensive Redis error handling;
    - Support extensible key generation via RedisKeySchema.

Classes:
    UserRedisDAO:
        DAO for managing user quota data in a Redis datastore.

Example:
    >>> from cloudshortener.dao.redis import UserRedisDAO
    >>> dao = UserRedisDAO(prefix="app:dev")

    >>> dao.quota("user123")
    0

    >>> dao.increment_quota("user123")
    1

TODO:
    - Add quota reset or monthly rollover mechanism.
    - Add support for quota usage analytics.
"""

from beartype import beartype

from cloudshortener.dao.base import UserBaseDAO
from cloudshortener.dao.redis.mixins import RedisClientMixin
from cloudshortener.dao.redis.helpers import handle_redis_connection_error
from cloudshortener.dao.exceptions import UserDoesNotExistError
from cloudshortener.utils.constants import ONE_MONTH_SECONDS


class UserRedisDAO(RedisClientMixin, UserBaseDAO):
    """Redis-based Data Access Object (DAO) for managing user quotas

    This class implements the UserBaseDAO interface using Redis as a datastore.

    Attributes (see RedisClientMixin):
        redis (redis.Redis):
            Redis client used to communicate with the Redis datastore.
        keys (RedisKeySchema):
            Key schema helper for generating namespaced Redis keys.

    Methods:
        quota(user_id: str, **kwargs) -> int:
            Retrieve or initialize a user's monthly quota counter.
            Automatically sets a one-month expiration when first initialized.
            Raises DataStoreError on connectivity issues with Redis.

        increment_quota(user_id: str, **kwargs) -> int:
            Increment the existing monthly quota for a user.
            Raises UserDoesNotExistError if the user quota key does not exist.
            Raises DataStoreError on connectivity issues with Redis.

    Example:
        >>> dao = UserRedisDAO(redis_host="localhost", prefix="users:prod")
        >>> dao.quota("user123")
        0
        >>> dao.increment_quota("user123")
        1
    """

    @handle_redis_connection_error
    @beartype
    def quota(self, user_id: str, **kwargs) -> int:
        """Retrieve or initialize the user's monthly quota

        If the user quota key does not exist, it is automatically initialized
        to zero and assigned a one-month expiration time.

        Args:
            user_id (str):
                The unique identifier of the user.
            **kwargs:
                Optional keyword arguments (for future use).

        Returns:
            int:
                The user's current monthly quota. Newly created keys return 0.

        Raises:
            DataStoreError:
                If Redis connection fails during retrieval or initialization.

        Example:
            >>> dao.quota("user123")
            0
        """
        user_quota_key = self.keys.user_quota_key(user_id)
        monthly_quota = self.redis.incrby(user_quota_key, 0)  # Initialize key if missing
        if monthly_quota == 0:
            self.redis.expire(user_quota_key, ONE_MONTH_SECONDS)
        return monthly_quota

    @handle_redis_connection_error
    @beartype
    def increment_quota(self, user_id: str, **kwargs) -> int:
        """Increment the user's monthly quota counter

        The quota key must already exist in Redis. If it does not, this method
        raises a UserDoesNotExistError to prevent unintended key creation.

        Args:
            user_id (str):
                The unique identifier of the user.
            **kwargs:
                Optional keyword arguments (for future use).

        Returns:
            int:
                The user's updated monthly quota after incrementing by one.

        Raises:
            UserDoesNotExistError:
                If the quota key for the user does not exist in Redis.
            DataStoreError:
                If Redis connection fails during the operation.

        Example:
            >>> dao.increment_quota("user123")
            1
        """
        user_quota_key = self.keys.user_quota_key(user_id)
        if not self.redis.exists(user_quota_key):
            raise UserDoesNotExistError(f"User with ID '{user_id}' does not exist.")
        return self.redis.incr(user_quota_key)
