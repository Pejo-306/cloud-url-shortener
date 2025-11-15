"""Data Access Object (DAO) implementation for managing shortened URLs in Redis

This module provides a Redis-based implementation of ShortURLBaseDAO for CRUD-like
operations with ShortURLModel instances.

Responsibilities:
    - Insert and retrieve short URLs from Redis;
    - Increment the global counter;
    - Maintain per-link metadata (e.g., hit counters, TTL);
    - Decrement monthly hit quotas for link access tracking;
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

    >>> leftover_hits = dao.hit("abc123")
    >>> leftover_hits
    9999

TODO:
    - Add support for configurable TTL and hit quotas.
"""

from datetime import datetime, timedelta, UTC

from beartype import beartype

from cloudshortener.models import ShortURLModel
from cloudshortener.dao.base import ShortURLBaseDAO
from cloudshortener.dao.redis.mixins import RedisClientMixin
from cloudshortener.dao.redis.helpers import handle_redis_connection_error
from cloudshortener.dao.exceptions import ShortURLAlreadyExistsError, ShortURLNotFoundError
from cloudshortener.utils.helpers import beginning_of_next_month
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

        get(shortcode: str, **kwargs) -> ShortURLModel:
            Retrieve a short URL mapping and its metadata (hits, expiry) by shortcode.
            Raises ShortURLNotFoundError when the shortcode doesn't exist.
            Raises DataStoreError on connectivity issues with Redis.

        hit(shortcode: str, **kwargs) -> int:
            Decrement the monthly hit counter for a short URL.
            Initializes the monthly quota key if it doesn't exist for the current month.
            Returns the remaining hits after decrement (may be negative if quota exceeded).
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
        >>> leftover_hits = dao.hit("abc123")
        >>> leftover_hits
        9999
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
            # fmt: off
            pipe.set(link_hits_key,
                     DEFAULT_LINK_HITS_QUOTA,
                     nx=True,
                     exat=int(beginning_of_next_month().timestamp()))
            # fmt: on
            pipe.execute()
        return self

    @handle_redis_connection_error
    @beartype
    def get(self, shortcode: str, **kwargs) -> ShortURLModel:
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
            ShortURLModel:
                The retrieved ShortURLModel instance if found.

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

        if original_url is None:
            raise ShortURLNotFoundError(f"Short URL with code '{shortcode}' not found.")

        return ShortURLModel(
            target=original_url,
            shortcode=shortcode,
            hits=hits,
            expires_at=datetime.now(UTC) + timedelta(seconds=ttl),
        )

    @handle_redis_connection_error
    @beartype
    def hit(self, shortcode: str, **kwargs) -> int:
        """Decrement the monthly hit counter for a short URL.

        NOTE: if the link hits counter for this month still hasn't been isntantiated,
              this method is responsible for setting this month's link hit counter with
              the default link hit quota and set to expire by the beginning of next month
              (YYYY-MM+1-01T00:00:00Z in UTC).
        NOTE: the method will decrement the link hits quota value below 0 to avoid multiple
              Redis network round trip for validity checks. It is the application's responsibility
              to handle negative link hit counter values.

        Args:
            shortcode (str):
                The short code of the ShortURLModel to be retrieved.

            **kwargs:
                Additional keyword arguments, used by data store.

        Return:
            int:
                leftover link hits for this month.

        Raises:
            ShortURLNotFoundError:
                If no short URL with the given short code exists.

            DataStoreError:
                If Redis connectivity issues occur.

        Example:
            >>> dao.hit('abc123')
            9999
        """
        link_url_key = self.keys.link_url_key(shortcode)
        link_hits_key = self.keys.link_hits_key(shortcode)

        if not self.redis.exists(link_url_key):
            raise ShortURLNotFoundError(f"Short URL with code '{shortcode}' not found.")

        # NOTE: The SET NX and DECR commands are executed as an atomic operation
        #       to avoid race conditions where a concurrent request might steal race
        #       preference from another concurrent request by decrementing below the link hits quota.

        #       e.g. if <quota> == 1 in this example:
        #
        #       (lambda 1): ShortURLRedisDAO.hit():
        #                   -> SET <app>:links:<shortcode>:hits:<YYYY-MM> <quota> NX EXAT <expiry>
        #                   ... interruption
        #       (lambda 2): ShortURLRedisDAO.hit():
        #                   -> SET <app>:links:<shortcode>:hits:<YYYY-MM> <quota> NX EXAT <expiry>
        #                   -> DECR <app>:links:<shortcode>:hits:<YYYY-MM>
        #                   (returned value) => 0
        #       (lambda 1): ShortURLRedisDAO.hit() continued...:
        #                   -> DECR <app>:links:<shortcode>:hits:<YYYY-MM>
        #                   => Both lambdas decrement, but only one initializes correctly
        #                   (returned value) => -1
        #
        #       So even though (lambda 1) initialized the link hits quota key first to 1,
        #       (lambda 2) gets to decrement the link hits quota first. Therefore, (lambda 2)'s
        #       redirection request continues successfully, while (lambda 1)'s redirection request is
        #       limitted.
        with self.redis.pipeline(transaction=True) as pipe:
            # fmt: off
            pipe.set(link_hits_key,
                     DEFAULT_LINK_HITS_QUOTA,
                     nx=True,
                     exat=int(beginning_of_next_month().timestamp()))
            # fmt: on
            pipe.decr(link_hits_key)
            _, leftover_hits = pipe.execute()

        return leftover_hits

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
