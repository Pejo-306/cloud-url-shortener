import json
from typing import Any, Dict

import redis

from cloudshortener.models import ShortURLModel
from cloudshortener.dao.redis import ShortURLRedisDAO
from cloudshortener.lambdas.shorten_url.shortener import shorten_url


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

    # TODO: retrieve original_url from the the Post request
    # TODO: return 400 error if there is no original URL
    # TODO: initialize nad handle redis client inside ShortURLRedisDAO
    # TODO: move configuration for DAO's outside the lambda and load them via lambda
    # TODO BONUS: track & adjust user quota in database
    # TODO: pipeline all redis operations for performance

    # 0- Extract original URL from request
    # original_url = event.get('original_url')
    original_url = 'https://lambda.hello.com/'

    # 1- Create DAO class to access short URL records
    redis_client = redis.Redis(host='redis', port=6379, db=0, decode_responses=True)
    short_url_dao = ShortURLRedisDAO(redis_client=redis_client, prefix='cloudshortener:local')

    # 2- Get counter from database (via DAO)
    counter = short_url_dao.count(increment=True)

    # 3- Generate short_url from counter
    short_code = shorten_url(counter, salt='my_secret', length=7)

    # 4- Store short_url and original_url mapping in database (via DAO)
    short_url = ShortURLModel(short_code=short_code, original_url=original_url)
    short_url_dao.insert(short_url=short_url)

    return {
        "statusCode": 200,
        "body": json.dumps({
            "message": "Hello from Shorten URL Lambda!",
            'counter': counter,
            'original_url': original_url,
            'short_code': short_code,
            'short_url': repr(short_url_dao)
        }),
    }
