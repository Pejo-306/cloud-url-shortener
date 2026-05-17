import base64
import binascii
import json
import logging

import functions_framework
from flask import Request
from flask.typing import ResponseReturnValue

from cloudshortener.cloud.functions.shorten.handler import cors_headers, shorten
from cloudshortener.cloud.functions.types import ShortenConfig, ShortenRequest
from cloudshortener.cloud.gcp.config import load_config
from cloudshortener.constants import FunctionName
from cloudshortener.utils import app_prefix

logger = logging.getLogger(__name__)


def extract_user_id(request: Request) -> str | None:
    """Decode Firebase JWT payload from API Gateway header (already validated upstream).

    Cloud Endpoints / API Gateway forwards the JWT payload base64-encoded in
    ``X-Apigateway-Api-Userinfo`` after validating the ``Authorization`` bearer token.
    """
    userinfo = request.headers.get('X-Apigateway-Api-Userinfo')
    if not userinfo:
        return None
    padded = userinfo + '=' * (-len(userinfo) % 4)
    try:
        raw = base64.urlsafe_b64decode(padded)
    except (binascii.Error, ValueError):
        logger.exception('Failed to decode X-Apigateway-Api-Userinfo as URL-safe base64: userinfo=%s.', userinfo)
        return None

    try:
        payload = json.loads(raw.decode('utf-8'))
    except (json.JSONDecodeError, UnicodeDecodeError):
        logger.exception('Failed to parse decoded userinfo JSON: raw=%s.', raw)
        return None
    sub = payload.get('sub')
    return sub if isinstance(sub, str) else None


@functions_framework.http
def shorten_url(request: Request) -> ResponseReturnValue:
    if request.method == 'OPTIONS':
        return ('', 204, cors_headers())

    try:
        raw_config = load_config(FunctionName.SHORTEN_URL)
    except Exception as e:
        logger.exception('Failed to load shorten config from GCS: %s.', e)
        body = json.dumps({'message': 'Internal Server Error'})
        return (body, 500, {**cors_headers(), 'Content-Type': 'application/json'})
    else:
        redis_config = raw_config['redis']
        config = ShortenConfig(
            redis_host=redis_config['host'],
            redis_port=int(redis_config['port']),
            redis_db=int(redis_config['db']),
            redis_username=redis_config.get('username'),
            redis_password=redis_config.get('password'),
            app_prefix=app_prefix(),
        )

    user_id = extract_user_id(request)
    base_url = request.host_url.rstrip('/')
    req = ShortenRequest(
        user_id=user_id,
        body=request.get_data(as_text=True),
        base_url=base_url,
    )

    logger.debug('Assuming Redis as the backend database for short URLs')
    result = shorten(req, config)
    return (result.body, result.status_code, result.headers)
