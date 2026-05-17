import json
import logging

import functions_framework
from flask import Request
from flask.typing import ResponseReturnValue

from cloudshortener.cloud.functions.redirect.handler import cors_headers, redirect
from cloudshortener.cloud.functions.types import RedirectConfig, RedirectRequest
from cloudshortener.cloud.gcp.config import load_config
from cloudshortener.constants import FunctionName
from cloudshortener.utils import app_prefix

logger = logging.getLogger(__name__)


def extract_shortcode(request: Request) -> str | None:
    """Extract the shortcode segment from the request path.

    GCP API Gateway is configured with path_translation: APPEND_PATH_TO_ADDRESS,
    which appends the matched path (e.g. /{shortcode}) to the Cloud Function URL.
    The shortcode is the last non-empty segment of the resulting path.
    """
    segments = [s for s in request.path.split('/') if s]
    return segments[-1] if segments else None


@functions_framework.http
def redirect_url(request: Request) -> ResponseReturnValue:
    if request.method == 'OPTIONS':
        return ('', 204, cors_headers())

    try:
        raw_config = load_config(FunctionName.REDIRECT_URL)
    except Exception as e:
        logger.exception('Failed to load redirect config from GCS: %s.', e)
        body = json.dumps({'message': 'Internal Server Error'})
        return (body, 500, {**cors_headers(), 'Content-Type': 'application/json'})
    else:
        redis_config = raw_config['redis']
        config = RedirectConfig(
            redis_host=redis_config['host'],
            redis_port=int(redis_config['port']),
            redis_db=int(redis_config['db']),
            redis_username=redis_config.get('username'),
            redis_password=redis_config.get('password'),
            app_prefix=app_prefix(),
        )

    shortcode = extract_shortcode(request)
    base = request.host_url.rstrip('/')
    short_url = f'{base}/{shortcode}' if shortcode else base
    req = RedirectRequest(shortcode=shortcode, short_url=short_url)

    logger.debug('Assuming Redis as the backend database for short URLs')
    result = redirect(req, config)
    return (result.body, result.status_code, result.headers)
