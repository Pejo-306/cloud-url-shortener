import json

import redis

from cloudshortener.models import ShortURLModel
from cloudshortener.dao.redis import ShortURLRedisDAO


def lambda_handler(event, context):
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


    """

    shortcode = str(event.get('pathParameters', {}).get('shortcode'))
    # TODO: if shortcode is none => return 400 error

    # 1- Create DAO class to access short URL records
    redis_config = {
        'redis_host': 'redis',
        'redis_port': 6379,
        'redis_db': 0,
        'redis_decode_responses': True
    }
    short_url_dao = ShortURLRedisDAO(**redis_config, prefix='cloudshortener:local')

    # 2- Get short_url record from database
    short_url = short_url_dao.get(short_code=shortcode)

    return {
        'statusCode': 302,
        'body': json.dumps({
            'message': "Hello from Redirect URL Lambda!",
            'shortcode': short_url.short_code,
            'original_url': short_url.original_url,
            'expires_at': short_url.expires_at.isoformat(),
            'ttl': short_url.expires_at.timestamp(),
            'short_url': str(short_url_dao),
        }),
    }


