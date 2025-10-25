from datetime import datetime, timedelta
from typing import Optional

import redis

from cloudshortener.models import ShortURLModel
from cloudshortener.dao.base import ShortURLBaseDAO
from cloudshortener.dao.redis import RedisKeySchema
from cloudshortener.dao.exceptions import DataStoreError, ShortURLAlreadyExistsError, ShortURLNotFoundError


ONE_YEAR_SECONDS = 31_536_000


class ShortURLRedisDAO(ShortURLBaseDAO):

    def __init__(self, redis_client: redis.Redis, prefix: Optional[str] = None):
        self.redis = redis_client
        self.keys = RedisKeySchema(prefix=prefix)
    
    def insert(self, short_url: ShortURLModel, **kwargs) -> 'ShortURLRedisDAO':
        # TODO: validate short url has valid data before insertion
        # TODO: remove hardcoded values and add them via constructur (with defaults)
        # TODO: add Redis pipelining for performance boost
        # TODO: Add error handling
        link_url_key = self.keys.link_url_key(short_url.short_code)
        link_hits_key = self.keys.link_hits_key(short_url.short_code)

        self.redis.set(link_url_key, short_url.original_url, ex=ONE_YEAR_SECONDS)
        self.redis.set(link_hits_key, 10000, ex=ONE_YEAR_SECONDS)
        return self

    def get(self, short_code: str, **kwargs) -> ShortURLModel | None:
        # TODO: add error handling
        # TODO: add auto decoding from Redis
        # TODO: add hits to ShortURLModel
        link_url_key = self.keys.link_url_key(short_code)
        link_hits_key = self.keys.link_hits_key(short_code)

        original_url = self.redis.get(link_url_key)
        hits = self.redis.get(link_hits_key)
        ttl = self.redis.ttl(link_url_key)

        if original_url is None or hits is None:
            raise ShortURLNotFoundError(f"Short URL with code '{short_code}' not found.")

        return ShortURLModel(
            short_code=short_code,
            original_url=original_url.decode('utf-8'),
            expires_at=datetime.utcnow() + timedelta(seconds=int(ttl.decode('utf-8'))),
        )
