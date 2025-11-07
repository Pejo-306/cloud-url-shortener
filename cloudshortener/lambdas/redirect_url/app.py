import json
from typing import Any

from cloudshortener.dao.redis import ShortURLRedisDAO
from cloudshortener.dao.exceptions import ShortURLNotFoundError
from cloudshortener.utils import load_config, get_short_url, app_prefix


def lambda_handler(event: dict[str, Any], context: Any) -> dict[str, Any]:
    """Handle incoming API Gateway requests to redirect URLs

    This Lambda handler follows this procedure to redirect URLs:
    - Step 1: Extract shortcode from request path
    - Step 2: Initialize DAO subclass
    - Step 3: Get short URL record from database
    - Step 4: Redirect client to target URL

    HTTP responses:
        302: Successful redirect
            headers:
                Location: target URL destination
        400: Bad client request
            message: missing or invalid shortcode in path parameters
        500: Internal server error
            message: server experienced an internal error

    Args:
        event (Dict[str, Any]):
            API Gateway event payload containing the shortcode path parameter.
        context (Any):
            AWS Lambda runtime context object (not used directly).

    Returns:
        Dict[str, Any]:
            API Gateway-compatible response including statusCode, headers, and body.

    Example:
        >>> event = {'pathParameters': {'shortcode': 'Gh71TCN'}}
        >>> response = lambda_handler(event, None)
        >>> response['statusCode']
        302
        >>> response['headers']['Location']
        'https://example.com/my-page'
    """
    # TODO: move the prefix creation to a helper function?
    # TODO: add error handling for invalid short code
    # TODO: add lambda handling of a short URL already exists in shorten_url

    # 0- Get application's config
    try:
        app_config = load_config('redirect_url')
    except FileNotFoundError:
        return {
            'statusCode': 500,
            'body': json.dumps(
                {
                    'message': 'Internal Server Error',
                }
            ),
        }

    # 1- Extract shortcode from request's path
    shortcode = event.get('pathParameters', {}).get('shortcode')
    if shortcode is None:
        return {
            'statusCode': 400,
            'body': json.dumps(
                {
                    'message': "Bad Request (missing 'shortcode' in path)",
                }
            ),
        }

    # 2- Create DAO class to access short URL records
    redis_config = {f'redis_{k}': v for k, v in app_config['redis'].items()}
    short_url_dao = ShortURLRedisDAO(**redis_config, prefix=app_prefix())

    # 3- Get short_url record from database
    try:
        short_url = short_url_dao.get(shortcode=shortcode)
    except ShortURLNotFoundError:
        return {
            'statusCode': 400,
            'body': json.dumps(
                {
                    'message': f"Bad Request (short url {get_short_url(shortcode, event)} doesn't exist)",
                }
            ),
        }
    else:
        target_url = short_url.target

    return {
        'statusCode': 302,
        'headers': {
            'Location': target_url,
            # TODO: remove later (Needed only for temporary frontend)
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Headers': 'Content-Type',
            'Access-Control-Allow-Methods': 'OPTIONS,POST,GET',
        },
        'body': json.dumps({}),  # no body needed for redirects
    }
