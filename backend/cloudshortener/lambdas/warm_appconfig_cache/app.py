import json
import logging

from cloudshortener.types import LambdaEvent, LambdaContext, LambdaDiagnosticResponse
from cloudshortener.dao.cache import AppConfigCacheDAO
from cloudshortener.dao.exceptions import CacheMissError, CachePutError, DataStoreError, DAOError
from cloudshortener.utils.config import app_prefix
from cloudshortener.lambdas.warm_appconfig_cache.constants import SUCCESS, ERROR


logger = logging.getLogger(__name__)


def response_success(*, appconfig_version: int) -> LambdaDiagnosticResponse:
    return json.dumps(
        {
            'status': SUCCESS,
            'appconfig_version': int(appconfig_version),
            'message': f'Successfully warmed cache with AppConfig version {appconfig_version}',
        }
    )


def response_error(*, error: DAOError | Exception) -> LambdaDiagnosticResponse:
    return json.dumps(
        {
            'status': ERROR,
            'message': 'Failed to warm up cache with latest AppConfig',
            'reason': str(error),
            'error': error.__class__.__name__,
        }
    )


def lambda_handler(event: LambdaEvent, context: LambdaContext) -> LambdaDiagnosticResponse:
    """Warm ElastiCache with newest AppConfig deployment document.

    Diagnostic responses (NOT valid HTTP responses):
        `success`:
            status: success
            appconfig_version: <version>
            message: Successfully warmed cache with AppConfig version <version>
        `error`:
            status: error
            message: Failed to warm up cache with latest AppConfig
            reason: <reason>
            error: <error class name> (e.g. CacheMissError, CachePutError, DataStoreError)
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
