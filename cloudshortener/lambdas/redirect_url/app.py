import json
from typing import Dict, Any

from cloudshortener.dao.redis import ShortURLRedisDAO
from cloudshortener.utils import load_config, app_env, app_name


def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """Sample pure Lambda function

    Parameters
    ----------
    event: dict, required
        API Gateway Lambda Proxy Input Format

        Event doc: https://docs.aws.amazon.com/apigateway/latest/developerguide/set-up-lambda-proxy-integrations.html#api-gateway-simple-proxy-for-lambda-input-format

    context: object, required
        Lambda Context runtime methods and attributes

        Context doc: https://docs.aws.amazon.com/lambda/latest/dg/python-context-object.html

    Returns
    ------
    API Gateway Lambda Proxy Output Format: dict

        Return doc: https://docs.aws.amazon.com/apigateway/latest/developerguide/set-up-lambda-proxy-integrations.html
    """

    """
    {
        "pathParameters": {
            "shortcode": "Gh71TCN"
        }
    }

    {"APP_ENV":"local","APP_NAME":"cloudshortener","PROJECT_ROOT":"/var/task/"}
    """

    # 0- Get application's config
    try:
        app_config = load_config('redirect_url')
    except FileNotFoundError:
        return {
            'statusCode': 500,
            'body': json.dumps({
                'message': "Internal Server Error",
            }),
        }

    # 1- Extract shortcode from request's path
    shortcode = str(event.get('pathParameters', {}).get('shortcode'))
    if shortcode is None:
        return {
            'statusCode': 400,
            'body': json.dumps({
                'message': "Bad Request (missing 'shortcode' in path)",
            }),
        }

    # 2- Create DAO class to access short URL records
    redis_config = {f'redis_{k}': v for k, v in app_config['redis'].items()}
    # TODO: move the prefix creation to a helper function?
    # TODO: add error handling for Redis connection error
    prefix = None if app_name() is None else f'{app_name()}:{app_env()}'
    short_url_dao = ShortURLRedisDAO(**redis_config, prefix=prefix)

    # 3- Get short_url record from database
    # TODO: add error handling for invalid short codes
    short_url = short_url_dao.get(short_code=shortcode)
    original_url = short_url.original_url

    return {
        'statusCode': 302,
        'headers': {
            'Location': original_url,
        },
        'body': ''  # no body needed for redirects
    }
