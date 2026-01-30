import json
import logging
from datetime import datetime, UTC

from cloudshortener.types import LambdaEvent, LambdaContext, LambdaResponse
from cloudshortener.dao.redis import ShortURLRedisDAO
from cloudshortener.dao.exceptions import ShortURLNotFoundError
from cloudshortener.utils import load_config, get_short_url, app_prefix
from cloudshortener.utils.helpers import beginning_of_next_month, guarantee_500_response
from cloudshortener.lambdas.redirect_url.constants import (
    MISSING_SHORTCODE,
    SHORT_URL_NOT_FOUND,
    LINK_QUOTA_EXCEEDED,
    REDIRECT_SUCCESS,
)


logger = logging.getLogger(__name__)


def cors_headers() -> dict[str, str]:
    """API gateway returns these CORS headers to allow frontend on another domain to process the response."""
    return {
        'Access-Control-Allow-Origin': '*',  # TODO: this should be a specific frontend domain only
        'Access-Control-Allow-Headers': 'Content-Type',
        'Access-Control-Allow-Methods': 'OPTIONS,POST,GET',
    }


def response_500(message: str | None = None) -> LambdaResponse:
    base = 'Internal Server Error'
    body = {'message': base if not message else f'{base} ({message})'}
    return {
        'statusCode': 500,
        'headers': cors_headers(),
        'body': json.dumps(body),
    }


def response_400(message: str | None = None, error_code: str | None = None) -> LambdaResponse:
    base = 'Bad Request'
    body = {'message': base if not message else f'{base} ({message})'}
    if error_code:
        body['errorCode'] = error_code
    return {
        'statusCode': 400,
        'headers': cors_headers(),
        'body': json.dumps(body),
    }


def response_429(*, retry_after: int, message: str | None = None, error_code: str | None = None) -> LambdaResponse:
    body = {'message': message or 'Too Many Requests'}
    if error_code:
        body['errorCode'] = error_code
    headers = cors_headers()
    headers['Content-Type'] = 'application/json'
    headers['Retry-After'] = str(retry_after)
    return {
        'statusCode': 429,
        'headers': headers,
        'body': json.dumps(body),
    }


def response_302(*, location: str) -> LambdaResponse:
    headers = cors_headers()
    headers['Location'] = location
    return {
        'statusCode': 302,
        'headers': headers,
        'body': json.dumps({}),  # no body needed for redirects
    }


@guarantee_500_response
def lambda_handler(event: LambdaEvent, context: LambdaContext) -> LambdaResponse:
    """Redirect short URL to original long URL.

    Procedure:
        - Step 1: Extract shortcode from request path
        - Step 2: Hit the link and check if quota is exceeded
        - Step 3: Get short URL record from database
        - Step 4: Redirect client to target URL

    HTTP responses:
        302: Successful redirect
            headers:
                Location: target URL destination
        400: Bad client request
            message: missing or invalid shortcode in path parameters
        429: Too many requests
            message: monthly hit quota exceeded for link
        500: Internal server error
            message: server experienced an internal error
    """
    # 0- Get application's config
    try:
        app_config = load_config('redirect_url')
    except FileNotFoundError:
        logger.exception('Failed to load AppConfig for redirect URL function. Responding with 500.')
        return response_500()
    else:
        logger.debug('Assuming Redis as the backend database for short URLs')
        redis_config = {f'redis_{k}': v for k, v in app_config['redis'].items()}

    # 1- Extract shortcode from request's path
    shortcode = event.get('pathParameters', {}).get('shortcode')
    if shortcode is None:
        logger.info(
            'Missing "shortcode" in path. Responding with 400.',
            extra={'event': MISSING_SHORTCODE},
        )
        return response_400(message="missing 'shortcode' in path", error_code=MISSING_SHORTCODE)
    logger.debug('Client requested short URL %s.', get_short_url(shortcode, event))

    short_url_dao = ShortURLRedisDAO(**redis_config, prefix=app_prefix())

    # 2- Hit the link and check if quota is exceeded
    try:
        leftover_hits = short_url_dao.hit(shortcode=shortcode)
    except ShortURLNotFoundError:
        logger.info(
            'Short URL record not found in database. Responding with 400.',
            extra={'shortcode': shortcode, 'event': SHORT_URL_NOT_FOUND},
        )
        return response_400(message=f"short url {get_short_url(shortcode, event)} doesn't exist", error_code=SHORT_URL_NOT_FOUND)
    else:
        logger.debug('Short URL record (shortcode: %s) found in database.', shortcode)

        if leftover_hits < 0:
            logger.info(
                'Monthly hit quota exceeded for link. Responding with 429.',
                extra={'shortcode': shortcode, 'event': LINK_QUOTA_EXCEEDED},
            )

            reset_dt = beginning_of_next_month()
            reset_date = reset_dt.strftime('%Y-%m-%dT%H:%M:%SZ')
            ttl_to_reset = int((reset_dt - datetime.now(UTC)).total_seconds())
            return response_429(
                retry_after=ttl_to_reset,
                error_code=LINK_QUOTA_EXCEEDED,
                message=f'Monthly hit quota exceeded for link. Try again after {reset_date}.',
            )
        else:
            logger.debug(
                'Leftover monthly hits: %s.',
                leftover_hits,
                extra={'shortcode': shortcode, 'leftover_hits': leftover_hits},
            )

    # 3- Get short_url record from database
    try:
        short_url = short_url_dao.get(shortcode=shortcode)
    except ShortURLNotFoundError:  # pragma: no cover
        logger.info(
            'Short URL record not found in database. Responding with 400.',
            extra={
                'shortcode': shortcode,
                'event': SHORT_URL_NOT_FOUND,
                'reason': 'Possible race condition encountered (short URL record just expired)',
            },
        )
        return response_400(message=f"short url {get_short_url(shortcode, event)} doesn't exist", error_code=SHORT_URL_NOT_FOUND)
    else:
        target_url = short_url.target

    # 4- Redirect client to target URL
    logger.info(
        'Redirecting client to target URL. Responding with 302.',
        extra={'shortcode': shortcode, 'event': REDIRECT_SUCCESS},
    )
    return response_302(location=target_url)
