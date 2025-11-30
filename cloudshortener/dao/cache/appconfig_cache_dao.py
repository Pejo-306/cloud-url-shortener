"""DAO for caching AWS AppConfig documents in Redis (ElastiCache)

This module provides a Redis-backed cache for AWS AppConfig documents with an
on-demand fallback to the AppConfig APIs when cache entries are missing.

Responsibilities:
    - Retrieve AppConfig documents and metadata from Redis
    - On cache-miss (and when configured), fetch from AppConfig and populate cache
    - Maintain three key types (no TTL applied):
        * <prefix>:appconfig:latest            -> latest document JSON (string)
        * <prefix>:appconfig:v{n}              -> versioned document JSON (string)
        * <prefix>:appconfig:v{n}:metadata     -> versioned metadata JSON (string)

Classes:
    AppConfigCacheDAO:
        Concrete DAO for AppConfig caching backed by Redis. Uses ElastiCacheClientMixin
        to initialize the Redis client (AWS/LocalStack aware) and assigns CacheKeySchema
        for key generation.

Example:
    Basic usage with cache-warming on misses:

        >>> dao = AppConfigCacheDAO(prefix="cloudshortener:dev")

        # Retrieve the latest AppConfig document; warms cache if missing.
        >>> doc = dao.latest(pull=True)
        >>> isinstance(doc, dict)
        True
        >>> sorted(doc.keys())[:3]
        ['active_backend', 'configs', 'redirect_url']  # example keys (may vary)

        # Retrieve a specific version; warms cache if missing.
        >>> v12 = dao.get(12, pull=True)
        >>> v12 == doc  # not necessarily equal; depends on current 'latest' vs version 12
        False

        # Retrieve metadata for a version; warms cache if missing.
        >>> meta = dao.metadata(12, pull=True)
        >>> meta  # doctest: +ELLIPSIS
        {'version': 12, 'etag': 'W/"...etag..."', 'content_type': 'application/json', 'fetched_at': '2025-...Z'}

        # Access the same values from cache (Cache HITs) without reaching AppConfig:
        >>> cached_latest = dao.latest(pull=False)
        >>> cached_v12 = dao.get(12, pull=False)
        >>> cached_meta_v12 = dao.metadata(12, pull=False)

NOTE:
    - This DAO intentionally couples cache access with AppConfig fetching to keep the
      interface simple at call sites. If the cache is cold, the DAO can populate it
      by contacting AppConfig (when pull=True).

TODO: add unit tests!
"""

import json
import os
from datetime import datetime, UTC
from typing import Any

import boto3
import redis
from beartype import beartype

from cloudshortener.dao.cache.mixins import ElastiCacheClientMixin
from cloudshortener.dao.exceptions import CacheMissError, CachePutError
from cloudshortener.dao.redis.helpers import handle_redis_connection_error
from cloudshortener.utils.helpers import require_environment
from cloudshortener.utils.constants import (
    APPCONFIG_APP_ID_ENV,
    APPCONFIG_ENV_ID_ENV,
    APPCONFIG_PROFILE_ID_ENV,
)


class AppConfigCacheDAO(ElastiCacheClientMixin):
    """Redis-backed DAO for AppConfig documents with on-demand fetch/caching

    Attributes (via mixins):
        redis (redis.Redis):
            Redis client used to communicate with the ElastiCache/Redis datastore.
        keys (CacheKeySchema):
            Key schema helper for generating namespaced AppConfig cache keys.

    Methods:
        latest(pull: bool = True) -> dict:
            Retrieve the latest AppConfig document.
            On miss, optionally fetch from AppConfig and populate cache.

        get(version: int | str, pull: bool = True) -> dict:
            Retrieve a specific version of the AppConfig document, or 'latest'.
            On miss, optionally fetch from AppConfig and populate cache.

        metadata(version: int, pull: bool = True) -> dict:
            Retrieve metadata for a specific AppConfig version.
            On miss, optionally fetch from AppConfig and populate cache.

    Example:
        >>> dao = AppConfigCacheDAO(prefix="cloudshortener:dev")
        >>> dao.latest()          # dict
        >>> dao.get(10)           # dict
        >>> dao.metadata(10)      # dict
    """

    @handle_redis_connection_error
    @beartype
    def latest(self, pull: bool = True) -> dict[str, Any]:
        """Retrieve the latest AppConfig document

        This method stores the full JSON document under the '<prefix>:appconfig:latest'
        key to avoid two round trips to Redis. Internally, it delegates to get('latest').

        Args:
            pull (bool):
                If True, fetch the 'latest' document from AppConfig and cache on miss.
                If False, raise CacheMissError on miss.
                Defaults to True.

        Returns:
            dict[str, Any]: The AppConfig JSON document.

        Raises:
            CacheMissError:
                If the 'latest' document is not cached and pull is False.
            CachePutError:
                If the 'latest' document cannot be written to the cache after fetch.
            ValueError:
                If environment variables required for AppConfig are missing.
            DataStoreError:
                If a Redis connectivity issue occurs (handled by decorator).
        """
        return self.get('latest', pull=pull)

    @handle_redis_connection_error
    @beartype
    def get(self, version: int | str, pull: bool = True) -> dict[str, Any]:
        """Retrieve a versioned (or latest) AppConfig document

        Steps:
            - If version == 'latest', try "<prefix>:appconfig:latest".
              Else try "<prefix>:appconfig:v{version}".
            - On CACHE HIT, load appconfig document as deserialized JSON object (Python dictionary)
            - On CACHE MISS, raise CacheMissError if pull=False. Otherwise, fetch
              the document from AppConfig (which also warms the cache as a side effect)

        Args:
            version (int | str):
                Either an integer version or the string 'latest'.
            pull (bool):
                If True, fetch from AppConfig and cache on miss.
                If False, raise CacheMissError on miss.
                Defaults to True.

        Returns:
            dict[str, Any]: The AppConfig JSON document.

        Raises:
            CacheMissError:
                If the requested document is not cached and pull is False.
            CachePutError:
                If the AppConfig document cannot be written to the cache after fetch.
            ValueError:
                If environment variables required for AppConfig are missing.
            DataStoreError:
                If a Redis connectivity issue occurs (handled by decorator).
        """
        if version == 'latest':
            key = self.keys.appconfig_latest_key()
        else:
            key = self.keys.appconfig_version_key(int(version))
        appconfig_document_blob = self.redis.get(key)

        # CACHE HIT: load appconfig document as deserialized JSON object (Python dictionary)
        if appconfig_document_blob is not None:
            return json.loads(appconfig_document_blob)

        # CACHE MISS: raise CacheMissError if pull=False
        #             otherwise fetch the document from AppConfig
        if not pull:
            label = 'latest' if version == 'latest' else f'v{int(version)}'
            raise CacheMissError(f'AppConfig {label} not found in cache and pull=False.')

        _, document, _ = self._pull_appconfig(version)
        return document

    @handle_redis_connection_error
    @beartype
    def metadata(self, version: int, pull: bool = True) -> dict[str, Any]:
        """Retrieve metadata for a specific AppConfig version

        Steps:
            - Try "<prefix>:appconfig:v{version}:metadata".
            - On CACHE HIT, load appconfig metadata as deserialized JSON object (Python dictionary)
            - On CACHE MISS, raise CacheMissError if pull=False. Otherwise, fetch
              the metadata from AppConfig (which also warms the cache as a side effect)

        Args:
            version (int):
                Hosted configuration version to retrieve metadata for.
            pull (bool):
                If True, fetch from AppConfig and cache on miss.
                If False, raise CacheMissError on miss.
                Defaults to True.

        Returns:
            dict[str, Any]:
                Metadata object:
                    {
                      "version": int,
                      "etag": str | None,
                      "content_type": str | None,
                      "fetched_at": ISO-8601 string
                    }

        Raises:
            CacheMissError:
                If the metadata is not cached and pull is False.
            CachePutError:
                If the metadata cannot be written to the cache after fetch.
            ValueError:
                If environment variables required for AppConfig are missing.
            DataStoreError:
                If a Redis connectivity issue occurs (handled by decorator).
        """
        key = self.keys.appconfig_metadata_key(int(version))
        appconfig_metadata_blob = self.redis.get(key)

        # CACHE HIT: load appconfig metadata as deserialized JSON object (Python dictionary)
        if appconfig_metadata_blob is not None:
            return json.loads(appconfig_metadata_blob)

        # CACHE MISS: raise CacheMissError if pull=False
        #             otherwise fetch the metadata from AppConfig
        if not pull:
            raise CacheMissError(f'AppConfig v{version} metadata not found in cache and pull=False.')

        _, _, metadata = self._pull_appconfig(int(version))
        return metadata

    @beartype
    def _pull_appconfig(self, version: int | str) -> tuple[int, dict[str, Any], dict[str, Any]]:
        """Fetch the requested AppConfig document + metadata and warm the cache

        Behavior:
            - If version == 'latest', uses the AppConfig Data API and writes both:
              * <prefix>:appconfig:v{resolved_version}
              * <prefix>:appconfig:v{resolved_version}:metadata
              * <prefix>:appconfig:latest (duplicate of document, for faster HITs)
            - If version is an int, uses the AppConfig control-plane API to fetch
              the specific hosted configuration version and writes the versioned keys.

        Args:
            version (int | str):
                Either the string 'latest' or a concrete integer version.

        Returns:
            tuple[int, dict[str, Any], dict[str, Any]]:
                (resolved_version, document_dict, metadata_dict)

        Raises:
            ValueError:
                If required AppConfig environment variables are missing or response headers
                are malformed (e.g., no configuration version).
            CachePutError:
                If a Redis connection error occurs while writing fetched values to the cache.
        """
        if version == 'latest':
            resolved_version, document, metadata = self._fetch_latest_appconfig()
        else:
            resolved_version, document, metadata = self._fetch_appconfig(int(version))

        self._warm_up_cache(
            resolved_version=resolved_version,
            document=document,
            metadata=metadata,
            latest=(version == 'latest'),
        )
        return resolved_version, document, metadata

    @beartype
    def _warm_up_cache(
        self,
        resolved_version: int,
        document: dict[str, Any],
        metadata: dict[str, Any],
        latest: bool = False,
    ) -> None:
        """Write fetched AppConfig content and metadata to Redis

        Args:
            resolved_version (int):
                The concrete version number resolved from the fetch operation.
            document (dict[str, Any]):
                The AppConfig document JSON (already parsed).
            metadata (dict[str, Any]):
                Metadata for the document (version, etag, content_type, fetched_at).
            latest (bool):
                If True, also set '<prefix>:appconfig:latest' to the same document.

        Returns:
            None

        Raises:
            CachePutError:
                If the Redis writes fail due to connectivity or other Redis errors.
        """
        content_key = self.keys.appconfig_version_key(resolved_version)
        meta_key = self.keys.appconfig_metadata_key(resolved_version)
        latest_key = self.keys.appconfig_latest_key()

        document_json = json.dumps(document, separators=(',', ':'), ensure_ascii=False)
        metadata_json = json.dumps(metadata, separators=(',', ':'), ensure_ascii=False)

        try:
            with self.redis.pipeline(transaction=True) as pipe:
                pipe.set(content_key, document_json)
                pipe.set(meta_key, metadata_json)
                if latest:
                    pipe.set(latest_key, document_json)  # duplicate full doc for faster retrieval
                pipe.execute()
        except redis.exceptions.ConnectionError as e:
            raise CachePutError(f'Failed to write AppConfig v{resolved_version} to cache.') from e

    @require_environment(APPCONFIG_APP_ID_ENV, APPCONFIG_ENV_ID_ENV, APPCONFIG_PROFILE_ID_ENV)
    @beartype
    def _fetch_latest_appconfig(self) -> tuple[int, dict[str, Any], dict[str, Any]]:
        """Fetch the latest AppConfig document via the AppConfig Data API

        Environment:
            APPCONFIG_APP_ID, APPCONFIG_ENV_ID, APPCONFIG_PROFILE_ID must be set.

        Returns:
            tuple[int, dict[str, Any], dict[str, Any]]:
                (resolved_version, document, metadata)

        Raises:
            ValueError:
                If required environment variables are missing;
                OR if the response lacks a configuration version header;
                OR if the version header is invalid.
            botocore.exceptions.BotoCoreError / ClientError:
                If the AppConfig Data API calls fail.
        """
        app_id = os.environ[APPCONFIG_APP_ID_ENV]
        env_id = os.environ[APPCONFIG_ENV_ID_ENV]
        profile_id = os.environ[APPCONFIG_PROFILE_ID_ENV]

        # Get latest configuration from AppConfig Data API
        client = boto3.client('appconfigdata')
        token = client.start_configuration_session(
            ApplicationIdentifier=app_id,
            EnvironmentIdentifier=env_id,
            ConfigurationProfileIdentifier=profile_id,
        )['InitialConfigurationToken']
        resp = client.get_latest_configuration(ConfigurationToken=token)

        # Parse the response body into a deserialized JSON object (Python dictionary)
        body = resp['Configuration']
        content = body.read() if hasattr(body, 'read') else body
        document = json.loads((content or b'').decode('utf-8'))

        # Extract the configuration version from the response headers
        headers = (resp.get('ResponseMetadata') or {}).get('HTTPHeaders') or {}
        version_str = headers.get('configuration-version') or headers.get('x-amzn-appconfig-configuration-version')
        if not version_str:
            raise ValueError('AppConfig Data response missing configuration version header.')
        try:
            resolved_version = int(version_str)
        except (TypeError, ValueError) as e:
            raise ValueError(f'Invalid configuration-version header: {version_str!r}') from e

        metadata = {
            'version': resolved_version,
            'etag': headers.get('etag'),
            'content_type': resp.get('ContentType'),
            'fetched_at': datetime.now(UTC).isoformat(),
        }
        return resolved_version, document, metadata

    @require_environment(APPCONFIG_APP_ID_ENV, APPCONFIG_PROFILE_ID_ENV)
    @beartype
    def _fetch_appconfig(self, version: int) -> tuple[int, dict[str, Any], dict[str, Any]]:
        """Fetch a specific hosted AppConfig version via the control-plane API

        Environment:
            APPCONFIG_APP_ID, APPCONFIG_PROFILE_ID must be set.

        Args:
            version (int):
                The hosted configuration version to fetch.

        Returns:
            tuple[int, dict[str, Any], dict[str, Any]]:
                (version, document, metadata)

        Raises:
            ValueError:
                If required environment variables are missing.
            botocore.exceptions.BotoCoreError / ClientError:
                If the AppConfig control-plane API call fails.
        """
        app_id = os.environ[APPCONFIG_APP_ID_ENV]
        profile_id = os.environ[APPCONFIG_PROFILE_ID_ENV]

        # Fetch the specific hosted configuration version from AppConfig control-plane API
        client = boto3.client('appconfig')
        resp = client.get_hosted_configuration_version(
            ApplicationId=app_id,
            ConfigurationProfileId=profile_id,
            VersionNumber=version,
        )

        # Parse the response body into a deserialized JSON object (Python dictionary)
        body = resp.get('Content')
        content = body.read() if hasattr(body, 'read') else body
        document = json.loads((content or b'').decode('utf-8'))

        # Extract the etag from the response headers
        etag = (resp.get('ResponseMetadata') or {}).get('HTTPHeaders', {}).get('etag')
        metadata = {
            'version': version,
            'etag': etag,
            'content_type': resp.get('ContentType'),
            'fetched_at': datetime.now(UTC).isoformat(),
        }
        return version, document, metadata
