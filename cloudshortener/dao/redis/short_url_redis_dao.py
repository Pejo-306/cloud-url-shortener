"""Data Access Object (DAO) implementation for managing shortened URLs in Redis

This module provides a Redis-based implementation of ShortURLBaseDAO for CRUD-like
operations with ShortURLModel instances.

Responsibilities:
    - Insert and retrieve short URLs from Redis;
    - Increment the global counter;
    - Maintain per-link metadata (e.g., hit counters, TTL);
    - Provide defensive error handling and raise appropriate DAO exceptions.

Classes:
    ShortURLRedisDAO:
        DAO for storing and retrieving ShortURLModel in a Redis datastore.

Example:
    >>> from cloudshortener.models import ShortURLModel
    >>> from cloudshortener.dao.redis import ShortURLRedisDAO

    >>> dao = ShortURLRedisDAO(prefix="app:dev")

    >>> short_url = ShortURLModel(
    ...     target="https://example.com/page",
    ...     shortcode="abc123"
    ... )
    >>> dao.insert(model)
    <ShortURLRedisDAO>

    >>> retrieved = dao.get("abc123")
    >>> retrieved.target
    'https://example.com/page'
    >>> retrieved.shortcode
    'abc123'
    >>> retrieved.hits
    10000
    >>> retrieved.expires_at
    <datetime>

TODO:
    - Add quota decrement functionality for hits management.
    - Add support for configurable TTL and hit quotas.
"""

from datetime import datetime, timedelta

from beartype import beartype

from cloudshortener.models import ShortURLModel
from cloudshortener.dao.base import ShortURLBaseDAO
from cloudshortener.dao.redis.mixins import RedisClientMixin
from cloudshortener.dao.redis.helpers import handle_redis_connection_error
from cloudshortener.dao.exceptions import ShortURLAlreadyExistsError, ShortURLNotFoundError
from cloudshortener.utils.constants import ONE_YEAR_SECONDS, DEFAULT_LINK_HITS_QUOTA


class ShortURLRedisDAO(RedisClientMixin, ShortURLBaseDAO):
    """Redis-based Data Access Object (DAO) for managing short URL mappings

    This class implements the ShortURLBaseDAO interface using Redis as a data store.

    Attributes (see RedisClientMixin):
        redis (redis.Redis):
            Redis client used to communicate with the Redis datastore.
        keys (RedisKeySchema):
            Key schema helper for generating namespaced Redis keys.

    Methods:
        insert(short_url: ShortURLModel, **kwargs) -> ShortURLRedisDAO:
            Insert a short URL mapping and initialize its hit counter.
            Raises ShortURLAlreadyExistsError when a URL with the same shortcode exists.
            Raises DataStoreError on connectivity issues with Redis.

        get(shortcode: str, **kwargs) -> ShortURLModel | None:
            Retrieve a short URL mapping and its metadata (hits, expiry) by shortcode.
            Raises ShortURLNotFoundError when the shortcode doesn't exist.
            Raises DataStoreError on connectivity issues with Redis.

        count(increment: bool = False, **kwargs) -> int:
            Retrieve (and optionally increment) the global URL counter.
            Raises DataStoreError on connectivity issues with Redis.

    Example:
        >>> dao = ShortURLRedisDAO(redis_host="localhost", prefix="shortener:test")
        >>> short_url = ShortURLModel(target="https://example.com", shortcode="abc123")
        >>> dao.insert(short_url)
        <ShortURLRedisDAO>
        >>> dao.get("abc123").target
        'https://example.com'
    """
    
    @handle_redis_connection_error
    @beartype
    def insert(self, short_url: ShortURLModel, **kwargs) -> 'ShortURLRedisDAO':
        """Insert a short URL mapping into Redis

        The insertion is performed via a Redis transaction (to avoid race conditions).
        Both the URL and its hit quota are stored with the same TTL to maintain
        consistency between related keys.

        Args:
            short_url (ShortURLModel):
                ShortURLModel instance representing the shortened URL mapping.
            **kwargs:
                Optional keyword arguments (for future use).

        Returns:
            ShortURLRedisDAO: self (for method chaining)

        Raises:
            ShortURLAlreadyExistsError:
                If a short URL with the same shortcode already exists.
            DataStoreError:
                If a Redis connection issue occurs during the transaction.

        Example:
            >>> short_url = ShortURLModel(
            ...     target='https://example.com',
            ...     shortcode='abc123'
            ... )
            >>> dao.insert(short_url)
            <ShortURLRedisDAO>
        """
        link_url_key = self.keys.link_url_key(short_url.shortcode)
        link_hits_key = self.keys.link_hits_key(short_url.shortcode)
        if self.redis.exists(link_url_key):
            raise ShortURLAlreadyExistsError(f"Short URL with code '{short_url.shortcode}' already exists.")

        # NOTE: The two SET commands are executed as an atomic operation
        #       to avoid a state where the short URL link is created but the
        #       monthly hits quota is not set. Therefore, it's possible to get
        #       a link without the monthly quota:
        #
        #       (lambda 1): ShortURLRedisDAO.insert():
        #                   -> SET <app>:links:<shortcode>:url <original url> EX <ttl>
        #                   ... interruption
        #       (lambda 2): ShortURLRedisDAO.get():
        #                   -> GET <app>:links:<shortcode>:url
        #                   -> GET <app>:links:<shortcode>:hits  => returns 'nil'
        #                   -> TTL <app>:links:<shortcode>:url
        #       (lambda 1): ShortURLRedisDAO.insert() continued...:
        #                   -> SET <app>:links:<shortcode>:hits <monthly link quota> EX <ttl>
        with self.redis.pipeline(transaction=True) as pipe:
            pipe.set(link_url_key, short_url.target, ex=ONE_YEAR_SECONDS)
            pipe.set(link_hits_key, DEFAULT_LINK_HITS_QUOTA, ex=ONE_YEAR_SECONDS)
            pipe.execute()
        return self

    @handle_redis_connection_error
    @beartype
    def get(self, shortcode: str, **kwargs) -> ShortURLModel | None:
        """Retrieve a stored short URL mapping by shortcode

        Fetches both the original URL and its associated hits counter using
        a single Redis transaction (to avoid race conditions). Calculates the
        expiry datetime from the remaining TTL value.

        Args:
            shortcode (str):
                The shortcode identifier for the shortened URL.
            **kwargs:
                Optional keyword arguments (for future use).

        Returns:
            ShortURLModel | None:
                The retrieved ShortURLModel instance if found.
                TODO: add option to avoid raising a ShortURLNotFoundError

        Raises:
            ShortURLNotFoundError:
                If the short URL does not exist in Redis.
            DataStoreError:
                If Redis connectivity issues occur.

        Example:
            >>> dao.get('abc123')
            ShortURLModel(target='https://example.com', shortcode='abc123', ...)
        """
        link_url_key = self.keys.link_url_key(shortcode)
        link_hits_key = self.keys.link_hits_key(shortcode)

        # TODO: once I add link quota management, add a comment explaining
        #       the possible race condition where I get a link with less hits than
        #       expected
        with self.redis.pipeline(transaction=True) as pipe:
            pipe.get(link_url_key)
            pipe.get(link_hits_key)
            pipe.ttl(link_url_key)
            original_url, hits, ttl = pipe.execute()

        if original_url is None or hits is None:
            raise ShortURLNotFoundError(f"Short URL with code '{shortcode}' not found.")

        return ShortURLModel(
            target=original_url,
            shortcode=shortcode,
            hits=hits,
            expires_at=datetime.utcnow() + timedelta(seconds=ttl),
        )

    @handle_redis_connection_error
    def count(self, increment: bool = False, **kwargs) -> int:
        """Retrieve global short URL counter

        Args:
            increment (bool):
                If True, increments the counter. Otherwise, retrieves its value.
            **kwargs:
                Optional keyword arguments.

        Returns:
            int:
                The updated or current global counter value.

        Example:
            >>> dao.count(increment=False)
            123
            >>> dao.count(increment=True)
            124
        """
        if increment:
            return self.redis.incr(self.keys.counter_key())
        else:
            return self.redis.get(self.keys.counter_key())
