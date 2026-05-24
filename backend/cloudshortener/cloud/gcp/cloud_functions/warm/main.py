import logging

import functions_framework
from cloudevents.http import CloudEvent

from cloudshortener.cloud.functions.types import WarmConfigCacheConfig, WarmConfigCacheRequest
from cloudshortener.cloud.functions.warm.handler import warm
from cloudshortener.cloud.gcp.dao.cache import GCPBackendConfigCacheDAO
from cloudshortener.utils import app_prefix

logger = logging.getLogger(__name__)


@functions_framework.cloud_event
def warm_config_cache(cloud_event: CloudEvent) -> None:
    """Warm MemoryStore cache when backend-config.json is updated in GCS."""
    data = cloud_event.data or {}
    logger.info(
        'Triggered backend config cache warm-up.',
        extra={
            'bucket': data.get('bucket'),
            'object_name': data.get('name'),
            'event_type': cloud_event.get('type'),
        },
    )

    request = WarmConfigCacheRequest()
    dao = GCPBackendConfigCacheDAO(prefix=app_prefix())
    config = WarmConfigCacheConfig(dao=dao)
    result = warm(request, config)

    logger.info('Warming result: status=%s body=%s', result.status_code, result.body)
