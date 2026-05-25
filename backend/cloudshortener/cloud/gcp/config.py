import functools
import json
import logging
import os
from collections.abc import Callable

from google.cloud import storage

from cloudshortener.types import FunctionConfiguration
from cloudshortener.constants import ENV, FunctionName
from cloudshortener.utils import app_prefix
from cloudshortener.utils.helpers import require_environment

logger = logging.getLogger(__name__)


def cache_backend_config(func: Callable) -> Callable:
    """Decorator: transparently cache backend-config documents via MemoryStore.

    Behavior:
        - On normal path:
            * Fetch latest backend-config document from MemoryStore cache.
            * Extract the per-function config for the requested function_name.
            * Return the same structure as the wrapped `load_config()`.
        - On any cache/infra/config error:
            * Fall back to the original `load_config()` implementation (GCS fetch).
    """

    @functools.wraps(func)
    def wrapper(function_name: FunctionName) -> FunctionConfiguration:
        from cloudshortener.cloud.gcp.dao.cache import GCPBackendConfigCacheDAO
        from cloudshortener.dao.exceptions import CacheMissError, CachePutError, DataStoreError
        from cloudshortener.exceptions import ConfigurationError, InfrastructureError, MalformedResponseError

        logger.info('Trying to load backend config from cache.', extra={'functionName': function_name})

        try:
            # Fetch the latest full backend-config document (pulling/warming cache on MISS)
            dao = GCPBackendConfigCacheDAO(prefix=app_prefix())
            document = dao.latest(pull=True)

        except (CacheMissError, CachePutError, DataStoreError, ConfigurationError, InfrastructureError, MalformedResponseError):
            # On any cache / config-structure / env-related issues, fall back
            # to the original (non-cached) implementation.
            return func(function_name)

        else:
            # Reproduce the existing load_config() behavior:
            active_backend = document['active_backend']
            function_config = document['configs'][function_name.value]

            logger.info('Loaded backend config from cache.', extra={'functionName': function_name, 'build': document['build']})
            return {active_backend: function_config[active_backend]}

    return wrapper


@cache_backend_config
@require_environment(ENV.GCP.CONFIG_GCS_BUCKET)
def load_config(function_name: FunctionName) -> FunctionConfiguration:
    """Load backend-config.json from GCS and return the active backend entry for `function_name`."""
    logger.info('Trying to load backend config from GCS.', extra={'functionName': function_name})

    bucket = os.environ[ENV.GCP.CONFIG_GCS_BUCKET]
    obj = os.environ.get(ENV.GCP.CONFIG_GCS_OBJECT, 'backend-config.json')

    client = storage.Client()
    blob = client.bucket(bucket).blob(obj)
    config = json.loads(blob.download_as_text())

    active_backend = config['active_backend']
    data = {active_backend: config['configs'][function_name.value][active_backend]}
    logger.info('Loaded backend config from GCS.', extra={'functionName': function_name.value, 'build': config['build']})
    return data
