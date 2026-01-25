from beartype import beartype

from cloudshortener.dao.base import UserBaseDAO
from cloudshortener.dao.redis.mixins import RedisClientMixin
from cloudshortener.dao.redis.helpers import handle_redis_connection_error
from cloudshortener.dao.exceptions import UserDoesNotExistError
from cloudshortener.utils.constants import ONE_MONTH_SECONDS


class UserRedisDAO(RedisClientMixin, UserBaseDAO):
    @handle_redis_connection_error
    @beartype
    def quota(self, user_id: str, **kwargs) -> int:
        user_quota_key = self.keys.user_quota_key(user_id)
        monthly_quota = self.redis.incrby(user_quota_key, 0)  # Initialize key if missing
        if monthly_quota == 0:  # Set new quota key to expire after 1 month
            self.redis.expire(user_quota_key, ONE_MONTH_SECONDS)
        return monthly_quota

    @handle_redis_connection_error
    @beartype
    def increment_quota(self, user_id: str, **kwargs) -> int:
        user_quota_key = self.keys.user_quota_key(user_id)
        if not self.redis.exists(user_quota_key):
            raise UserDoesNotExistError(f"User with ID '{user_id}' does not exist.")
        return self.redis.incr(user_quota_key)
