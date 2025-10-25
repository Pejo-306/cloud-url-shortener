import json
from typing import Any, Dict

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

    # try:
    #     ip = requests.get("http://checkip.amazonaws.com/")
    # except requests.RequestException as e:
    #     # Send some context about this error to Lambda Logs
    #     print(e)

    #     raise e

    # Lambda handler algorithm:
    # 1- Get and increment counter from database (via DAO)
    # 2- Generate short_url from counter
    # 3- Store short_url and original_url mapping in database (via DAO)
    # 4- TODO BONUS: track & adjust user quota in database

    return {
        "statusCode": 200,
        "body": json.dumps({
            "message": "Hello from Shorten URL Lambda!",
            # "location": ip.text.replace("\n", "")
        }),
    }
