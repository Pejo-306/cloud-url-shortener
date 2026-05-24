import json
import os
from datetime import UTC, datetime

from google.cloud import storage

from cloudshortener.types import BackendConfig, BackendConfigMetadata
from cloudshortener.constants import ENV
from cloudshortener.exceptions import BadConfigurationError
from cloudshortener.utils.helpers import require_environment
from cloudshortener.cloud.dao.base import BackendConfigCacheBaseDAO
from cloudshortener.cloud.dao.cache.constants import CacheTTL
from cloudshortener.cloud.gcp.dao.cache.mixins import MemoryStoreClientMixin


class GCPBackendConfigCacheDAO(BackendConfigCacheBaseDAO, MemoryStoreClientMixin):
    """Backend config cache DAO backed by GCS (source) + MemoryStore (cache).

    Reads the full backend-config.json document from GCS and caches it
    in MemoryStore with versioned + latest keys.

    The "version" is the integer `build` field in backend-config.json. Changing
    the build number triggers a cache warm-up.
    """

    def __init__(
        self,
        prefix: str | None = None,
        tls_verify: bool = False,
        ttl: int | None = CacheTTL.COOL,
        storage_client: storage.Client | None = None,
    ):
        super().__init__(prefix=prefix, tls_verify=tls_verify)
        self.ttl = ttl
        self._storage_client = storage_client

    @require_environment(ENV.GCP.CONFIG_GCS_BUCKET)
    def _fetch_from_source(self) -> tuple[int, BackendConfig, BackendConfigMetadata]:
        """Fetch backend-config.json from GCS."""
        bucket_name = os.environ[ENV.GCP.CONFIG_GCS_BUCKET]
        object_name = os.environ.get(ENV.GCP.CONFIG_GCS_OBJECT, 'backend-config.json')

        client = self._storage_client or storage.Client()
        blob = client.bucket(bucket_name).blob(object_name)
        raw = blob.download_as_text()

        try:
            document = json.loads(raw)
        except json.JSONDecodeError as e:
            raise BadConfigurationError(f'Invalid JSON in {object_name} from GCS bucket {bucket_name!r}') from e

        build = document.get('build')
        if build is None:
            raise BadConfigurationError(f'Missing "build" field in {object_name} from GCS bucket {bucket_name!r}')

        try:
            resolved_version = int(build)
        except (TypeError, ValueError) as e:
            raise BadConfigurationError(f'Invalid "build" field in {object_name}: {build!r}') from e

        metadata = {
            'version': resolved_version,
            'etag': blob.etag,
            'content_type': blob.content_type,
            'fetched_at': datetime.now(UTC).isoformat(),
        }
        return resolved_version, document, metadata
