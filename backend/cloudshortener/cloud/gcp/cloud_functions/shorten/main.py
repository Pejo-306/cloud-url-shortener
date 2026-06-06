import base64
import binascii
import json
import logging
import os
import functools

import functions_framework
from flask import Request
from flask.typing import ResponseReturnValue
from google.cloud import apigateway_v1

from cloudshortener.cloud.functions.shorten.handler import cors_headers, shorten
from cloudshortener.cloud.functions.types import ShortenConfig, ShortenRequest
from cloudshortener.cloud.gcp.config import load_config
from cloudshortener.constants import ENV, FunctionName
from cloudshortener.utils import app_prefix
from cloudshortener.utils.helpers import require_environment

logger = logging.getLogger(__name__)


@functools.cache
@require_environment(ENV.App.APP_NAME, ENV.App.APP_ENV, ENV.GCP.PROJECT_ID, ENV.GCP.REGION)
def get_api_gateway_base_url() -> str:
    """Resolve the public API Gateway base URL for this environment."""
    app_name = os.environ[ENV.App.APP_NAME]
    app_env = os.environ[ENV.App.APP_ENV]
    project_id = os.environ[ENV.GCP.PROJECT_ID]
    region = os.environ[ENV.GCP.REGION]
    gateway_id = f'{app_name}-{app_env}-gw'

    client = apigateway_v1.ApiGatewayServiceClient()
    resource_path = client.gateway_path(project_id, region, gateway_id)
    gateway = client.get_gateway(name=resource_path)
    return f'https://{gateway.default_hostname}'


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

    try:
        base_url = get_api_gateway_base_url()
    except Exception as e:
        logger.exception('Failed to resolve public API Gateway URL: %s.', e)
        body = json.dumps({'message': 'Internal Server Error'})
        return (body, 500, {**cors_headers(), 'Content-Type': 'application/json'})

    user_id = extract_user_id(request)
    req = ShortenRequest(
        user_id=user_id,
        body=request.get_data(as_text=True),
        base_url=base_url,
    )

    logger.debug('Assuming Redis as the backend database for short URLs')
    result = shorten(req, config)
    return (result.body, result.status_code, result.headers)
