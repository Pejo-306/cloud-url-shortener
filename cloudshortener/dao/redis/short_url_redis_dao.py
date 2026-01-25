from datetime import datetime, timedelta, UTC

from beartype import beartype  # TODO: remove this dependency

from cloudshortener.models import ShortURLModel
from cloudshortener.dao.base import ShortURLBaseDAO
from cloudshortener.dao.redis.mixins import RedisClientMixin
from cloudshortener.dao.redis.helpers import handle_redis_connection_error
from cloudshortener.dao.exceptions import ShortURLAlreadyExistsError, ShortURLNotFoundError
from cloudshortener.utils.helpers import beginning_of_next_month
from cloudshortener.utils.constants import ONE_YEAR_SECONDS, DEFAULT_LINK_HITS_QUOTA  # Add support for configurable TTL and hit quotas.


class ShortURLRedisDAO(RedisClientMixin, ShortURLBaseDAO):
    @handle_redis_connection_error
    @beartype
    def insert(self, short_url: ShortURLModel, **kwargs) -> 'ShortURLRedisDAO':
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
        link_url_key = self.keys.link_url_key(shortcode)
        link_hits_key = self.keys.link_hits_key(shortcode)

        # NOTE: we retrieve all values atomically to avoid a race condition where
        #       a concurrent request might decrement the link hits quota below 0.
        #       This would mess up our analytics:
        #
        #       (lambda 1): ShortURLRedisDAO.get():
        #                   -> GET <app>:links:<shortcode>:url
        #                   ... interruption
        #       (lambda 2): ShortURLRedisDAO.hit():
        #                   -> DECR <app>:links:<shortcode>:hits:<YYYY-MM>  => goes below 0
        #       (lambda 1): ShortURLRedisDAO.get() continued...:
        #                   -> GET <app>:links:<shortcode>:hits  => returns < 0 value
        #                   -> TTL <app>:links:<shortcode>:url
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

        If the link hits counter for this month still hasn't been instantiated,
        this method is responsible for setting this month's link hit counter with
        the default link hit quota and set it to expire by the beginning of next
        month (YYYY-MM+1-01T00:00:00Z in UTC).

        The method will decrement the link hits quota value below 0 to avoid
        multiple Redis network round trips for validity checks. It is the
        application's responsibility to handle negative link hit counter values.
        """
        link_url_key = self.keys.link_url_key(shortcode)
        link_hits_key = self.keys.link_hits_key(shortcode)

        if not self.redis.exists(link_url_key):
            raise ShortURLNotFoundError(f"Short URL with code '{shortcode}' not found.")

        # NOTE: The SET NX and DECR commands are executed as an atomic operation
        #       to avoid race conditions where a concurrent request might steal race
        #       preference from another concurrent request by decrementing below the link hits quota.
        #
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
        if increment:
            return self.redis.incr(self.keys.counter_key())
        else:
            return self.redis.get(self.keys.counter_key())
