import json
from typing import Any, Dict

from cloudshortener.models import ShortURLModel
from cloudshortener.dao.redis import ShortURLRedisDAO
from cloudshortener.utils import generate_shortcode, load_config, app_env, app_name, base_url


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
    {"APP_ENV":"local","APP_NAME":"cloudshortener","PROJECT_ROOT":"/var/task/"}
    """
    # TODO: document the function properly
    # TODO BONUS: track & adjust user quota in database
    # TODO: scramble counter to avoid sequential short_url values

    # 0- Get application's config
    try:
        app_config = load_config('shorten_url')
    except FileNotFoundError:
        return {
            'statusCode': 500,
            'body': json.dumps({
                'message': "Internal Server Error",
            }),
        }
    
    # 1- Extract original URL from request body
    try:
        request_body = json.loads(event.get('body') or '{}')
    except json.JSONDecodeError:
        return {
            'statusCode': 400,
            'body': json.dumps({
                'message': "Bad Request (invalid JSON body)",
            }),
        }
    target_url = request_body.get('target_url')
    if not target_url :
        return {
            'statusCode': 400,
            'body': json.dumps({
                'message': "Bad Request (missing 'target_url' in JSON body)",
            }),
        }

    # 2- Create DAO class to insert short URL records
    redis_config = {f'redis_{k}': v for k, v in app_config['redis'].items()}
    prefix = None if app_name() is None else f'{app_name()}:{app_env()}'
    short_url_dao = ShortURLRedisDAO(**redis_config, prefix=prefix)

    # 3- Get and increment counter from database (via DAO)
    counter = short_url_dao.count(increment=True)

    # 4- Generate short_url from counter
    shortcode = generate_shortcode(counter, salt='my_secret', length=7)

    # 5- Store short_url and original_url mapping in database (via DAO)
    short_url = ShortURLModel(shortcode=shortcode, target=target_url)
    short_url_dao.insert(short_url=short_url)
    # TODO: move short_url_string generation to the DAO or Model or helper function
    short_url_string = f'{base_url(event).rstrip("/")}/{shortcode}'

    # 6- Return successful response to user
    return {
        'statusCode': 200,
        'headers': {  # TODO: remove later (Needed only for temporary frontend)
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Headers': 'Content-Type',
            'Access-Control-Allow-Methods': 'OPTIONS,POST,GET',
        },
        'body': json.dumps({
            'message': f"Successfully shortened {target_url} to {short_url_string}",
            'target_url': target_url,
            'short_url': short_url_string,
            'shortcode': shortcode,
        }),
    }
