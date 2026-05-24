import json
import logging

from cloudshortener.cloud.functions.helpers import guarantee_500_response
from cloudshortener.cloud.functions.types import HttpResponse, WarmConfigCacheConfig, WarmConfigCacheRequest
from cloudshortener.cloud.functions.warm.constants import ERROR, SUCCESS
from cloudshortener.dao.exceptions import CacheMissError, CachePutError, DAOError, DataStoreError

logger = logging.getLogger(__name__)


def response_success(*, config_version: int) -> HttpResponse:
    return HttpResponse(
        status_code=200,
        headers={'Content-Type': 'application/json'},
        body=json.dumps(
            {
                'status': SUCCESS,
                'config_version': int(config_version),
                'message': f'Successfully warmed cache with backend config version {config_version}',
            }
        ),
    )


def response_error(*, error: DAOError | Exception) -> HttpResponse:
    return HttpResponse(
        status_code=500,
        headers={'Content-Type': 'application/json'},
        body=json.dumps(
            {
                'status': ERROR,
                'message': 'Failed to warm up cache with latest backend config',
                'reason': str(error),
                'error': error.__class__.__name__,
            }
        ),
    )


@guarantee_500_response
def warm(request: WarmConfigCacheRequest, config: WarmConfigCacheConfig) -> HttpResponse:
    """Warm cache with latest backend config document.

    Diagnostic responses:
        `success`:
            status: success
            config_version: <version>
            message: Successfully warmed cache with backend config version <version>
        `error`:
            status: error
            message: Failed to warm up cache with latest backend config
            reason: <reason>
            error: <error class name> (e.g. CacheMissError, CachePutError, DataStoreError)
    """
    warm_config_cache_dao = config.dao
    try:
        version = warm_config_cache_dao.version(force=True)
    except (CacheMissError, CachePutError, DataStoreError) as error:
        logger.exception(
            'Failed to warm config cache.',
            extra={
                'event': ERROR,
                'reason': str(error),
                'error': error.__class__.__name__,
            },
        )
        return response_error(error=error)
    else:
        logger.info(
            'Successfully warmed config cache with version %s.',
            version,
            extra={'event': SUCCESS, 'config_version': version},
        )
        return response_success(config_version=version)
