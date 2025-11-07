import json
from typing import Any

from cloudshortener.models import ShortURLModel
from cloudshortener.dao.redis import ShortURLRedisDAO, UserRedisDAO
from cloudshortener.dao.exceptions import ShortURLAlreadyExistsError
from cloudshortener.utils import generate_shortcode, load_config, get_short_url, app_prefix
from cloudshortener.utils.constants import DEFAULT_LINK_GENERATION_QUOTA


def lambda_handler(event: dict[str, Any], context: Any) -> dict[str, Any]:
    """Handle incoming API Gateway requests to shorten URLs

    This Lambda handler follows this procedure to shorten URLs:
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
        429: Too many link generation requests
            message: monthly user quota hit
        500: Internal server error
            message: indicate the server experieced an internal error

    Args:
        event (Dict[str, Any]):
            API Gateway event payload in Lambda Proxy format.
        context (Any):
            AWS Lambda context object containing runtime information.

    Returns:
        Dict[str, Any]:
            JSON-serializable response following API Gateway Lambda Proxy
            output format. Includes status code, headers, and response body.

    Example:
        >>> event = {'body': '{"target_url": "https://example.com"}'}
        >>> response = lambda_handler(event, None)
        >>> response['statusCode']
        200
        >>> json.loads(response['body'])['message']
        Successfully shortened https://example.com to https://mylambda.com/abc123
    """
    # TODO BONUS: track & adjust user quota in database
    # TODO: scramble counter to avoid sequential short_url values

    # 0- Get application's config
    try:
        app_config = load_config('shorten_url')
    except FileNotFoundError:
        return {
            'statusCode': 500,
            'body': json.dumps(
                {
                    'message': 'Internal Server Error',
                }
            ),
        }
    else:
        redis_config = {f'redis_{k}': v for k, v in app_config['redis'].items()}

    # 1- Extract user id from Cognito
    claims = event.get('requestContext', {}).get('authorizer', {}).get('claims', {})
    user_id = claims.get('sub')
    if user_id is None:
        return {
            'statusCode': 401,
            'body': json.dumps(
                {
                    'message': "Unathorized: missing 'sub' in JWT claims",
                }
            ),
        }

    # 2- Check if monthly quota is already reached
    user_dao = UserRedisDAO(**redis_config, prefix=app_prefix())
    user_quota = user_dao.quota(user_id=user_id)
    if user_quota >= DEFAULT_LINK_GENERATION_QUOTA:
        return {
            'statusCode': 429,
            'body': json.dumps(
                {
                    'message': 'Too many link generation requests: monthly quota reached',
                }
            ),
        }

    # 3- Extract original URL from request body
    try:
        request_body = json.loads(event.get('body') or '{}')
    except json.JSONDecodeError:
        return {
            'statusCode': 400,
            'body': json.dumps(
                {
                    'message': 'Bad Request (invalid JSON body)',
                }
            ),
        }
    target_url = request_body.get('target_url')
    if not target_url:
        return {
            'statusCode': 400,
            'body': json.dumps(
                {
                    'message': "Bad Request (missing 'target_url' in JSON body)",
                }
            ),
        }

    # 4- Generate shortcode for the new link
    short_url_dao = ShortURLRedisDAO(**redis_config, prefix=app_prefix())
    counter = short_url_dao.count(increment=True)
    shortcode = generate_shortcode(counter, salt='my_secret', length=7)

    # 5- Store short_url and target_url mapping in database (via DAO)
    try:
        short_url = ShortURLModel(shortcode=shortcode, target=target_url)
        short_url_dao.insert(short_url=short_url)
    except ShortURLAlreadyExistsError:
        return {
            'statusCode': 500,
            'body': json.dumps(
                {
                    'message': 'Internal Server Error',
                }
            ),
        }
    else:
        user_dao.increment_quota(user_id=user_id)
        short_url_string = get_short_url(shortcode, event)

    # 6- Return successful response to user
    return {
        'statusCode': 200,
        'headers': {  # TODO: remove later (Needed only for temporary frontend)
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Headers': 'Content-Type',
            'Access-Control-Allow-Methods': 'OPTIONS,POST,GET',
        },
        'body': json.dumps(
            {
                'message': f'Successfully shortened {target_url} to {short_url_string}',
                'target_url': target_url,
                'short_url': short_url_string,
                'shortcode': shortcode,
                'user_quota': user_quota,
                'new user_quota': user_quota + 1,
            }
        ),
    }
