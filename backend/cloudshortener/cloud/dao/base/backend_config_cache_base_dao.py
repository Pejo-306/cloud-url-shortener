import json
from abc import ABC, abstractmethod
from typing import cast

import redis

from cloudshortener.cloud.dao.cache import CacheKeySchema
from cloudshortener.types import BackendConfig, BackendConfigMetadata
from cloudshortener.dao.exceptions import CacheMissError, CachePutError
from cloudshortener.dao.redis.helpers import handle_redis_connection_error


class BackendConfigCacheBaseDAO(ABC):
    """Cached backend config base DAO with on-demand fetch/caching.

    Fetching behavior is controlled with the following flags, available in all public
    methods:
        - `pull` (bool): If True and cache miss, fetch the `latest` document from
          AppConfig and cache it. If False, raise `CacheMissError` on miss. Defaults
          to True.
        - `force` (bool): Always fetch the `latest` document from AppConfig and
          force cache. Defaults to False.

    Configurations and metadata are always stored as versioned keys in cache.
    They are also duplicated as `latest` version keys when the user accesses the
    latest application configuration. This speeds up retrieval (immediate GET
    instead of algorithmically looking for the latest versioned cache entry).

    The `version` parameter on methods can be a specific integer version or the
    string literal `latest`. If `latest` is requested, the DAO will use `latest`
    keys instead of versioned backend config keys.

    Configurations expire after a specific time, set by the `ttl` attribute, to
    avoid stale backend configurations.

    `BackendConfigMetadata` is a JSON object like:
    ```
        {
            "version": int,
            "etag": str | None,
            "content_type": str | None,
            "fetched_at": ISO-8601 string
        }
    ```

    Raises:
        `CacheMissError`:
            If the backend config is not cached and `pull` is False.
        `CachePutError`:
            If the backend config cannot be written to the cache after fetch.
        `DataStoreError`:
            If a Redis connectivity issue occurs.
    """

    redis: redis.Redis
    keys: CacheKeySchema
    ttl: int | None

    @handle_redis_connection_error
    def latest(self, pull: bool = True, force: bool = False) -> BackendConfig:
        return self.get('latest', pull=pull, force=force)

    @handle_redis_connection_error
    def version(self, pull: bool = True, force: bool = False) -> int:
        """Version number of the latest backend config document."""
        return self.metadata('latest', pull=pull, force=force)['version']

    @handle_redis_connection_error
    def get(self, version: int | str, pull: bool = True, force: bool = False) -> BackendConfig:
        # FORCE PULL: always fetch the document from the source and cache
        if force:
            _, document, _ = self._pull_config(version)
            return document

        if version == 'latest':
            key = self.keys.appconfig_latest_key()
        else:
            key = self.keys.appconfig_version_key(int(version))
        document_blob = self.redis.get(key)

        # CACHE HIT: load backend config document as deserialized JSON object (Python dictionary)
        if document_blob is not None:
            return json.loads(cast(str | bytes, document_blob))

        # CACHE MISS: raise CacheMissError if pull=False
        #             otherwise fetch the document from the source and cache
        if not pull:
            label = 'latest' if version == 'latest' else f'v{int(version)}'
            raise CacheMissError(f'Backend config {label} not found in cache and pull=False.')

        _, document, _ = self._pull_config(version)
        return document

    @handle_redis_connection_error
    def metadata(self, version: int | str, pull: bool = True, force: bool = False) -> BackendConfigMetadata:
        # FORCE PULL: always fetch the metadata from the source and cache
        if force:
            _, _, metadata = self._pull_config(version)
            return metadata

        if version == 'latest':
            key = self.keys.appconfig_latest_metadata_key()
        else:
            key = self.keys.appconfig_metadata_key(int(version))
        metadata_blob = self.redis.get(key)

        # CACHE HIT: load backend config metadata as deserialized JSON object (Python dictionary)
        if metadata_blob is not None:
            return json.loads(cast(str | bytes, metadata_blob))

        # CACHE MISS: raise CacheMissError if pull=False
        #             otherwise fetch the metadata from the source and cache
        if not pull:
            raise CacheMissError(f'Backend config v{version} metadata not found in cache and pull=False.')

        _, _, metadata = self._pull_config(version)
        return metadata

    def _pull_config(self, version: int | str) -> tuple[int, BackendConfig, BackendConfigMetadata]:
        """Fetch the requested backend config document + metadata and warm the cache.

        Behavior:
            - If version == 'latest', uses the backend config source and writes:
              * <prefix>:appconfig:v{resolved_version}
              * <prefix>:appconfig:v{resolved_version}:metadata
              * <prefix>:appconfig:latest (duplicate of document, for faster HITs)
              * <prefix>:appconfig:latest:metadata (duplicate of metadata, for faster HITs)
            - If version is an int, uses the backend config source to fetch
              the specific hosted configuration version and writes the versioned keys.
        """
        resolved_version, document, metadata = self._fetch_from_source()

        self._warm_up_cache(
            resolved_version=resolved_version,
            document=document,
            metadata=metadata,
            latest=(version == 'latest'),
        )
        return resolved_version, document, metadata

    def _warm_up_cache(
        self,
        resolved_version: int,
        document: BackendConfig,
        metadata: BackendConfigMetadata,
        latest: bool = False,
    ) -> None:
        content_key = self.keys.appconfig_version_key(resolved_version)
        meta_key = self.keys.appconfig_metadata_key(resolved_version)
        latest_key = self.keys.appconfig_latest_key()
        latest_meta_key = self.keys.appconfig_latest_metadata_key()

        document_json = json.dumps(document, separators=(',', ':'), ensure_ascii=False)
        metadata_json = json.dumps(metadata, separators=(',', ':'), ensure_ascii=False)

        try:
            with self.redis.pipeline(transaction=True) as pipe:
                pipe.set(content_key, document_json, ex=self.ttl)
                pipe.set(meta_key, metadata_json, ex=self.ttl)
                if latest:
                    pipe.set(latest_key, document_json, ex=self.ttl)
                    pipe.set(latest_meta_key, metadata_json, ex=self.ttl)
                pipe.execute()
        except redis.exceptions.ConnectionError as e:
            raise CachePutError(
                f'Failed to write backend config v{resolved_version} to cache. '
                '(hint: you may be using the read-only replica, ensure you are using the master)'
            ) from e

    @abstractmethod
    def _fetch_from_source(self) -> tuple[int, BackendConfig, BackendConfigMetadata]:
        """Fetch the latest backend config document from the provider-specific source."""
        ...
