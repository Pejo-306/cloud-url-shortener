import json
import logging

from cloudshortener.cloud.functions.helpers import guarantee_500_response
from cloudshortener.cloud.functions.shorten.constants import (
    INVALID_JSON,
    LINK_QUOTA_EXCEEDED,
    MISSING_TARGET_URL,
    MISSING_USER_ID,
    SHORTENING_SUCCESS,
    SHORT_URL_ALREADY_EXISTS,
)
from cloudshortener.cloud.functions.types import HttpResponse, ShortenConfig, ShortenRequest
from cloudshortener.constants import DefaultQuota
from cloudshortener.dao.exceptions import ShortURLAlreadyExistsError
from cloudshortener.dao.redis import ShortURLRedisDAO, UserRedisDAO
from cloudshortener.models import ShortURLModel
from cloudshortener.types import HttpHeaders
from cloudshortener.utils.shortener import generate_shortcode

logger = logging.getLogger(__name__)


def cors_headers() -> HttpHeaders:
    """CORS headers to allow frontend on another domain to process the response."""
    return {
        'Access-Control-Allow-Origin': '*',  # TODO: this should be a specific frontend domain only
        'Access-Control-Allow-Headers': 'Authorization,Content-Type',
        'Access-Control-Allow-Methods': 'OPTIONS,POST,GET',
    }


def response_500(message: str | None = None) -> HttpResponse:
    base = 'Internal Server Error'
    body = {'message': base if not message else f'{base} ({message})'}
    return HttpResponse(
        status_code=500,
        headers=cors_headers(),
        body=json.dumps(body),
    )


def response_401(message: str | None = None, error_code: str | None = None) -> HttpResponse:
    base = 'Unauthorized'
    body = {'message': base if not message else f'{base} ({message})'}
    if error_code:
        body['errorCode'] = error_code
    return HttpResponse(
        status_code=401,
        headers=cors_headers(),
        body=json.dumps(body),
    )


def response_400(message: str | None = None, error_code: str | None = None) -> HttpResponse:
    base = 'Bad Request'
    body = {'message': base if not message else f'{base} ({message})'}
    if error_code:
        body['errorCode'] = error_code
    return HttpResponse(
        status_code=400,
        headers=cors_headers(),
        body=json.dumps(body),
    )


def response_429(message: str | None = None, error_code: str | None = None) -> HttpResponse:
    base = 'Too Many Link Generation Requests'
    body = {'message': base if not message else f'{base} ({message})'}
    if error_code:
        body['errorCode'] = error_code
    return HttpResponse(
        status_code=429,
        headers=cors_headers(),
        body=json.dumps(body),
    )


def response_409(message: str | None = None, error_code: str | None = None) -> HttpResponse:
    base = 'Conflict'
    body = {'message': base if not message else f'{base} ({message})'}
    if error_code:
        body['errorCode'] = error_code
    return HttpResponse(
        status_code=409,
        headers=cors_headers(),
        body=json.dumps(body),
    )


def response_200(*, target_url: str, short_url: str, shortcode: str, user_quota: int) -> HttpResponse:
    return HttpResponse(
        status_code=200,
        headers=cors_headers(),
        body=json.dumps(
            {
                'message': f'Successfully shortened {target_url} to {short_url}',
                'targetUrl': target_url,
                'shortUrl': short_url,
                'shortcode': shortcode,
                'userQuota': user_quota,
                'remainingQuota': DefaultQuota.LINK_GENERATION - user_quota,
            }
        ),
    )


@guarantee_500_response
def shorten(request: ShortenRequest, config: ShortenConfig) -> HttpResponse:
    """Shorten a target URL using a provider-agnostic HTTP request.

    Procedure:
        - Step 1: Validate the authenticated user id from the request.
        - Step 2: Check whether the user's monthly link generation quota is reached.
        - Step 3: Parse the JSON body and read the camelCase targetUrl field.
        - Step 4: Generate a shortcode for the new link.
        - Step 5: Store the shortcode and target URL mapping in the configured datastore.
        - Step 6: Return the shortened URL and updated quota details.

    HTTP responses:
        200: Successful URL shortening
            message: success message
            targetUrl: original URL from the request
            shortUrl: newly generated short URL
            shortcode: newly generated shortcode
            userQuota: user's updated monthly link generation usage
            remainingQuota: remaining link generations this month
        400: Bad client request
            message: invalid JSON body or missing targetUrl
        401: Unauthorized
            message: missing authenticated user id
        409: Conflict
            message: short URL already exists
        429: Too many link generation requests
            message: monthly user quota reached
        500: Internal server error
            message: server experienced an internal error
    """
    # 1- Validate authenticated user id from request
    user_id = request.user_id
    if user_id is None:
        logger.info(
            'Unknown user id. Responding with 401.',
            extra={'event': MISSING_USER_ID},
        )
        return response_401(message="missing 'sub' in JWT claims", error_code=MISSING_USER_ID)

    # 2- Check if monthly user quota is already reached
    user_dao = UserRedisDAO(
        redis_host=config.redis_host,
        redis_port=config.redis_port,
        redis_db=config.redis_db,
        redis_username=config.redis_username,
        redis_password=config.redis_password,
        prefix=config.app_prefix,
    )
    user_quota = user_dao.quota(user_id=user_id)
    if user_quota >= DefaultQuota.LINK_GENERATION:
        logger.info('Monthly link generation quota reached. Responding with 429.', extra={'event': LINK_QUOTA_EXCEEDED})
        return response_429(message='monthly quota reached', error_code=LINK_QUOTA_EXCEEDED)
    logger.debug('Monthly link generation quota: %s.', user_quota, extra={'user_quota': user_quota})

    # 3- Extract target URL from request body
    try:
        request_body = json.loads(request.body or '{}')
    except json.JSONDecodeError:
        logger.info('Invalid JSON in request body. Responding with 400.', extra={'event': INVALID_JSON})
        return response_400(message='invalid JSON body', error_code=INVALID_JSON)

    target_url = request_body.get('targetUrl')
    if not target_url:
        logger.info("Missing 'targetUrl' in JSON body. Responding with 400.", extra={'event': MISSING_TARGET_URL})
        return response_400(message="missing 'targetUrl' in JSON body", error_code=MISSING_TARGET_URL)

    # 4- Generate shortcode for the new link
    short_url_dao = ShortURLRedisDAO(
        redis_host=config.redis_host,
        redis_port=config.redis_port,
        redis_db=config.redis_db,
        redis_username=config.redis_username,
        redis_password=config.redis_password,
        prefix=config.app_prefix,
    )
    counter = short_url_dao.count(increment=True)
    shortcode = generate_shortcode(counter, salt='my_secret', length=7)  # TODO: move salt and mult to secrets
    logger.debug('Generated shortcode: %s.', shortcode, extra={'shortcode': shortcode})

    # 5- Store short URL and target URL mapping in database
    try:
        short_url_model = ShortURLModel(shortcode=shortcode, target=target_url)
        short_url_dao.insert(short_url=short_url_model)
    except ShortURLAlreadyExistsError:
        logger.exception(
            'Short URL already exists. Responding with 409.',
            extra={
                'event': SHORT_URL_ALREADY_EXISTS,
                'shortcode': shortcode,
                'reason': 'Possible race condition encountered',
            },
        )
        return response_409(message='short URL already exists', error_code=SHORT_URL_ALREADY_EXISTS)
    else:
        new_user_quota = user_dao.increment_quota(user_id=user_id)
        base = request.base_url.rstrip('/')
        # TODO: use the public API Gateway URL instead of the Cloud Function URL.
        # In GCP, request.base_url is the Gen2 Cloud Function / Cloud Run URL, not
        # the user-facing API Gateway hostname. Terraform cannot wire the gateway
        # hostname into the function environment directly without creating a cycle:
        # the gateway depends on the function backend URI, while the function would
        # then depend on the gateway's generated hostname. A future deployment flow
        # should provide this as an external/static config value or patch config
        # after the gateway exists.
        short_url_string = f'{base}/{shortcode}'

    # 6- Return successful response to user
    logger.info(
        'Successfully shortened URL. Responding with 200.',
        extra={'event': SHORTENING_SUCCESS, 'shortcode': shortcode},
    )
    return response_200(
        target_url=target_url,
        short_url=short_url_string,
        shortcode=shortcode,
        user_quota=new_user_quota,
    )
