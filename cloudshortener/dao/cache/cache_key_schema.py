import functools
from collections.abc import Callable


__all__ = ['CacheKeySchema']  # hide internal decorator prefix_key from imports


def prefix_key(func: Callable) -> Callable:
    @functools.wraps(func)
    def wrapper(self, *args, **kwargs) -> str:
        key = func(self, *args, **kwargs)
        return f'{self.prefix}:{key}' if self.prefix is not None else key

    return wrapper


class CacheKeySchema:
    """Provide standardized Redis keys for storing AppConfig in ElastiCache.

    An optional prefix can be provided to namespace all generated keys.
    It is highly encouraged to set a custom prefix for each app and environment,
    e.g. "cloudshortener:prod" or "cloudshortener:dev".

    NOTE: Yes, this class mirrors RedisKeySchema, but we don't want to spaghettify
    the caching layer with our Redis datastore backend.
    """

    def __init__(self, prefix: str | None = None):
        if prefix is not None and not isinstance(prefix, str):
            raise TypeError(f'Prefix must be of type string (given type: {type(prefix)}).')

        self.prefix = f'cache:{prefix}' if prefix is not None else None

    @prefix_key
    def appconfig_latest_key(self) -> str:
        return 'appconfig:latest'

    @prefix_key
    def appconfig_latest_metadata_key(self) -> str:
        return 'appconfig:latest:metadata'

    @prefix_key
    def appconfig_version_key(self, version: int) -> str:
        return f'appconfig:v{int(version)}'

    @prefix_key
    def appconfig_metadata_key(self, version: int) -> str:
        return f'appconfig:v{int(version)}:metadata'
