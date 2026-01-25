import json
import logging
from typing import Any

from cloudshortener.models import ShortURLModel
from cloudshortener.dao.redis import ShortURLRedisDAO, UserRedisDAO
from cloudshortener.dao.exceptions import ShortURLAlreadyExistsError
from cloudshortener.utils import (
    generate_shortcode,
    load_config,
    get_short_url,
    app_prefix,
    guarantee_500_response,
    get_user_id,
)
from cloudshortener.utils.constants import DEFAULT_LINK_GENERATION_QUOTA
from cloudshortener.lambdas.shorten_url.constants import (
    MISSING_USER_ID,
    LINK_QUOTA_EXCEEDED,
    INVALID_JSON,
    MISSING_TARGET_URL,
    SHORT_URL_ALREADY_EXISTS,
    SHORTENING_SUCCESS,
)

logger = logging.getLogger(__name__)


# fmt: off
def response_500(message: str | None = None) -> dict:
    base = 'Internal Server Error'
    body = {'message': base if not message else f'{base} ({message})'}
    return {
        'statusCode': 500,
        'body': json.dumps(body),
    }


def response_401(message: str | None = None, error_code: str | None = None) -> dict:
    base = 'Unauthorized'
    body = {'message': base if not message else f'{base} ({message})'}
    if error_code:
        body['errorCode'] = error_code
    return {
        'statusCode': 401,
        'body': json.dumps(body),
    }


def response_400(message: str | None = None, error_code: str | None = None) -> dict:
    base = 'Bad Request'
    body = {'message': base if not message else f'{base} ({message})'}
    if error_code:
        body['errorCode'] = error_code
    return {
        'statusCode': 400,
        'body': json.dumps(body),
    }


def response_429(message: str | None = None, error_code: str | None = None) -> dict:
    base = 'Too Many Link Generation Requests'
    body = {'message': base if not message else f'{base} ({message})'}
    if error_code:
        body['errorCode'] = error_code
    return {
        'statusCode': 429,
        'body': json.dumps(body),
    }


def response_409(message: str | None = None, error_code: str | None = None) -> dict:
    base = 'Conflict'
    body = {'message': base if not message else f'{base} ({message})'}
    if error_code:
        body['errorCode'] = error_code
    return {
        'statusCode': 409,
        'body': json.dumps(body)
    }


def response_200(*, target_url: str, short_url: str, shortcode: str, user_quota: int) -> dict:
    return {
        'statusCode': 200,
        'headers': {
            # TODO: remove later (Needed only for temporary frontend)
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Headers': 'Content-Type',
            'Access-Control-Allow-Methods': 'OPTIONS,POST,GET',
        },
        'body': json.dumps(
            {
                'message': f'Successfully shortened {target_url} to {short_url}',
                'targetUrl': target_url,
                'shortUrl': short_url,
                'shortcode': shortcode,
                'userQuota': user_quota,
                'remainingQuota': DEFAULT_LINK_GENERATION_QUOTA - user_quota,
            }
        ),
    }
# fmt: on


@guarantee_500_response
def lambda_handler(event: dict, context: Any) -> dict:
    """Shorten target URL into a short URL

    Procedure:
    - Step 1: Extract Amazon Cognito user id from Lambda event
    - Step 2: Check if monthly user quota is reached
    - Step 3: Extract original URL from request body
    - Step 4: Generate shortcode for new link
    - Step 5: Store short_url and target_url mapping in database (via DAO)
    - Step 6: Respond to user with 200 success

    HTTP responses:
        200: Successful URL shortening
            message: success message
            target_url: original url (provided in request)
            short_url: newly generated short url
            shortcode: newly generated shortcode
        400: Bad client request
            message: indicate cause of bad request (invalid JSON or missing target_url)
        401: Unathorized
            message: indicate missing Cognito user_id
        409: Conflict
            message: indicate short URL already exists
        429: Too many link generation requests
            message: monthly user quota hit
        500: Internal server error
            message: indicate the server experieced an internal error
    """
    # 0- Get application's config
    try:
        app_config = load_config('shorten_url')
    except FileNotFoundError:
        logger.exception('Failed to load AppConfig for redirect URL function. Responding with 500.')
        return response_500()
    else:
        logger.debug('Assuming Redis as the backend database for short URLs')
        redis_config = {f'redis_{k}': v for k, v in app_config['redis'].items()}

    # 1- Extract user id from Cognito
    user_id = get_user_id(event)
    if user_id is None:
        logger.info(
            'Unknown user id. Responding with 401.',
            extra={'event': MISSING_USER_ID},
        )
        return response_401(message="missing 'sub' in JWT claims", error_code=MISSING_USER_ID)

    # 2- Check if monthly quota is already reached
    user_dao = UserRedisDAO(**redis_config, prefix=app_prefix())
    user_quota = user_dao.quota(user_id=user_id)
    if user_quota >= DEFAULT_LINK_GENERATION_QUOTA:
        logger.info('Monthly link generation quota reached. Responding with 429.', extra={'event': LINK_QUOTA_EXCEEDED})
        return response_429(message='monthly quota reached', error_code=LINK_QUOTA_EXCEEDED)
    logger.debug('Monthly link generation quota: %s.', user_quota, extra={'user_quota': user_quota})

    # 3- Extract original URL from request body
    try:
        request_body = json.loads(event.get('body') or '{}')
    except json.JSONDecodeError:
        logger.info('Invalid JSON in request body. Responding with 400.', extra={'event': INVALID_JSON})
        return response_400(message='invalid JSON body', error_code=INVALID_JSON)

    target_url = request_body.get('target_url') or request_body.get('targetUrl')
    if not target_url:
        logger.info("Missing 'target_url' or 'targetUrl' in JSON body. Responding with 400.", extra={'event': MISSING_TARGET_URL})
        return response_400(message="missing 'target_url' or 'targetUrl' in JSON body", error_code=MISSING_TARGET_URL)

    # 4- Generate shortcode for the new link
    short_url_dao = ShortURLRedisDAO(**redis_config, prefix=app_prefix())
    counter = short_url_dao.count(increment=True)
    shortcode = generate_shortcode(counter, salt='my_secret', length=7)  # TODO: move salt and mult to secrets
    logger.debug('Generated shortcode: %s.', shortcode, extra={'shortcode': shortcode})

    # 5- Store short_url and target_url mapping in database (via DAO)
    try:
        short_url = ShortURLModel(shortcode=shortcode, target=target_url)
        short_url_dao.insert(short_url=short_url)
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
        short_url_string = get_short_url(shortcode, event)

    # 6- Return successful response to user
    logger.info('Successfully shortened URL. Responding with 200.', extra={'event': SHORTENING_SUCCESS, 'shortcode': shortcode})
    return response_200(
        target_url=target_url,
        short_url=short_url_string,
        shortcode=shortcode,
        user_quota=new_user_quota,
    )
