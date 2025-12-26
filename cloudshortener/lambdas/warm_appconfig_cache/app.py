import json
import logging
from typing import Any

from cloudshortener.dao.cache import AppConfigCacheDAO
from cloudshortener.dao.exceptions import CacheMissError, CachePutError, DataStoreError, DAOError
from cloudshortener.utils.config import app_prefix
from cloudshortener.lambdas.warm_appconfig_cache.constants import SUCCESS, ERROR


logger = logging.getLogger(__name__)


def response_success(*, appconfig_version: int) -> dict:
    return json.dumps(
        {
            'status': SUCCESS,
            'appconfig_version': int(appconfig_version),
            'message': f'Successfully warmed cache with AppConfig version {appconfig_version}',
        }
    )


def response_error(*, error: DAOError | Exception) -> dict:
    return json.dumps(
        {
            'status': ERROR,
            'message': 'Failed to warm up cache with latest AppConfig',
            'reason': str(error),
            'error': error.__class__.__name__,
        }
    )


def lambda_handler(event: dict, context: Any) -> dict:
    """Warm ElastiCache with newest AppConfig deployment document

    This Lambda handler follows this procedure to shorten URLs:
    - Step 1: Pull and cache the latest AppConfig deployment document
    - Step 2: Respond with success or error

    Diagnostic responses:
        success:
            status: success
            appconfig_version: <version>
            message: Successfully warmed cache with AppConfig version <version>
        error:
            status: error
            message: Failed to warm up cache with latest AppConfig
            reason: <reason>
            error: <error class name> (e.g. CacheMissError, CachePutError, DataStoreError)

    Args:
        event (dict):
            EventBridge event payload.
        context (LambdaContext):
            AWS Lambda context object containing runtime information.

    Returns:
        dict:
            JSON-serializable response in Lambda Proxy format.

    TOOD: Example:
        >>> response = lambda_handler({}, None)
        >>> response['status']
        'success'
        >>> response['appconfig_version']
        123
        >>> response['message']
        'Successfully warmed cache with AppConfig version 123'
    """
    try:
        # Force pull the latest AppConfig document and cache it
        dao = AppConfigCacheDAO(prefix=app_prefix())
        version = dao.version(force=True)
    except (CacheMissError, CachePutError, DataStoreError) as error:
        logger.exception(
            'Failed to warm up cache with latest AppConfig.',
            extra={'event': ERROR, 'reason': str(error), 'error': error.__class__.__name__},
        )
        return response_error(error=error)
    else:
        logger.info(
            'Successfully warmed cache with AppConfig version %s.',
            version,
            extra={'event': SUCCESS, 'appconfig_version': version},
        )
        return response_success(appconfig_version=version)
