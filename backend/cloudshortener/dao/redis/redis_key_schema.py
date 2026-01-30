import functools
from collections.abc import Callable
from datetime import date


__all__ = ['RedisKeySchema']  # hide internal decorator prefix_key from imports


def prefix_key(func: Callable) -> Callable:
    @functools.wraps(func)
    def wrapper(self, *args, **kwargs) -> str:
        key = func(self, *args, **kwargs)
        return f'{self.prefix}:{key}' if self.prefix is not None else key

    return wrapper


class RedisKeySchema:
    """Provide standardized Redis keys for storing data models.

    An optional prefix can be provided to namespace all generated keys.
    It is highly encouraged to set a custom prefix for each app and environment,
    e.g. "cloudshortener:prod" or "cloudshortener:dev".
    """

    def __init__(self, prefix: str | None = None):
        if prefix is not None and not isinstance(prefix, str):
            raise TypeError(f'Prefix must be of type string (given type: {type(prefix)}).')

        self.prefix = prefix

    @prefix_key
    def link_url_key(self, short_code: str) -> str:
        return f'links:{short_code}:url'

    @prefix_key
    def link_hits_key(self, short_code: str) -> str:
        this_month = date.today().strftime('%Y-%m')
        return f'links:{short_code}:hits:{this_month}'

    @prefix_key
    def counter_key(self) -> str:
        return 'links:counter'

    @prefix_key
    def user_quota_key(self, user_id: str) -> str:
        this_month = date.today().strftime('%Y-%m')
        return f'users:{user_id}:quota:{this_month}'
