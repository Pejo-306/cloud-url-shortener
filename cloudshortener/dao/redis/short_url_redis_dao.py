from datetime import datetime, timedelta
from typing import Optional

import redis

from cloudshortener.models import ShortURLModel
from cloudshortener.dao.base import ShortURLBaseDAO
from cloudshortener.dao.redis import RedisKeySchema
from cloudshortener.dao.exceptions import DataStoreError, ShortURLAlreadyExistsError, ShortURLNotFoundError


ONE_YEAR_SECONDS = 31_536_000


class ShortURLRedisDAO(ShortURLBaseDAO):

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
    
    def insert(self, short_url: ShortURLModel, **kwargs) -> 'ShortURLRedisDAO':
        # TODO: validate short url has valid data before insertion
        # TODO: remove hardcoded values and add them via constructur (with defaults)
        # TODO: add Redis pipelining for performance boost
        # TODO: Add error handling
        # TODO: change short_code to shortcode everywhere
        link_url_key = self.keys.link_url_key(short_url.shortcode)
        link_hits_key = self.keys.link_hits_key(short_url.shortcode)

        # TODO: pipeline two set commands
        self.redis.set(link_url_key, short_url.target, ex=ONE_YEAR_SECONDS)
        self.redis.set(link_hits_key, 10000, ex=ONE_YEAR_SECONDS)
        return self

    def get(self, shortcode: str, **kwargs) -> ShortURLModel | None:
        # TODO: add error handling
        # TODO: add auto decoding from Redis
        # TODO: add hits to ShortURLModel
        # TODO: change short_code to shortcode everywhere
        link_url_key = self.keys.link_url_key(shortcode)
        link_hits_key = self.keys.link_hits_key(shortcode)

        # TODO: pipeline 3 commands
        original_url = self.redis.get(link_url_key)
        hits = self.redis.get(link_hits_key)
        ttl = self.redis.ttl(link_url_key)

        if original_url is None or hits is None:
            raise ShortURLNotFoundError(f"Short URL with code '{shortcode}' not found.")

        return ShortURLModel(
            target=original_url,
            shortcode=shortcode,
            expires_at=datetime.utcnow() + timedelta(seconds=ttl),
        )

    def count(self, increment: bool = False, **kwargs) -> int:
        # TODO: add error handling
        if increment:
            return self.redis.incr(self.keys.counter_key())
        else:
            return self.redis.get(self.keys.counter_key())

