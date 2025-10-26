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
    # try:
    #     ip = requests.get("http://checkip.amazonaws.com/")
    # except requests.RequestException as e:
    #     # Send some context about this error to Lambda Logs
    #     print(e)

    #     raise e

    """
    {
        "resource": "/{shortcode}",
        "path": "/abc1234",
        "httpMethod": "GET",
        "headers": {
            "Host": "localhost:3000",
            "User-Agent": "curl/8.5.0"
        },
        "queryStringParameters": null,
        "pathParameters": {
            "shortcode": "abc1234"
        },
        "requestContext": {
            "resourcePath": "/{shortcode}",
            "httpMethod": "GET",
            "path": "/{shortcode}",
            "domainName": "localhost",
            "stage": "Prod"
        },
        "body": null,
        "isBase64Encoded": false
    }

    """

    shortcode = str(event.get('pathParameters', {}).get('shortcode'))
    # TODO: if shortcode is none => return 400 error

    # 1- Create DAO class to access short URL records
    redis_client = redis.Redis(host='redis', port=6379, db=0, decode_responses=True)
    short_url_dao = ShortURLRedisDAO(redis_client=redis_client, prefix='cloudshortener:local')

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
            # "location": ip.text.replace("\n", "")
        }),
    }


