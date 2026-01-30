import json
import os
from datetime import datetime, UTC

import boto3
import redis
from botocore.client import BaseClient

from cloudshortener.constants import ENV
from cloudshortener.types import AppConfig, AppConfigMetadata
from cloudshortener.exceptions import AppConfigError
from cloudshortener.dao.cache.mixins import ElastiCacheClientMixin
from cloudshortener.dao.cache.constants import CacheTTL
from cloudshortener.dao.exceptions import CacheMissError, CachePutError
from cloudshortener.dao.redis.helpers import handle_redis_connection_error
from cloudshortener.utils.helpers import require_environment


class AppConfigCacheDAO(ElastiCacheClientMixin):
    """ElastiCache DAO for AppConfig documents with on-demand fetch/caching.

    Fetching behavior is controlled with the following flags, available in all public
    methods:
        - `pull` (bool): If True and cache miss, fetch the `latest` document from
          AppConfig and cache it. If False, raise `CacheMissError` on miss. Defaults
          to True.
        - `force` (bool): Always fetch the `latest` document from AppConfig and
          force cache. Defaults to False.

    Configurations and metadata are always stored as versioned keys in ElastiCache.
    They are also duplicated as `latest` version keys when the user accesses the
    latest application configuration. This speeds up retrieval (immediate GET
    instead of algorithmically looking for the latest versioned cache entry).

    The `version` parameter on methods can be a specific integer version or the
    string literal `latest`. If `latest` is requested, the DAO will use `latest`
    keys instead of versioned AppConfig keys.

    Configurations expire after a specific time, set by the `ttl` attribute, to
    avoid stale application configurations.

    `AppConfigMetadata` is a JSON object like:
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
            If the AppConfig is not cached and `pull` is False.
        `CachePutError`:
            If the AppConfig cannot be written to the cache after fetch.
        `DataStoreError`:
            If a Redis connectivity issue occurs.
    """

    def __init__(
        self,
        prefix: str | None = None,
        ssm_client: BaseClient | None = None,
        secrets_client: BaseClient | None = None,
        redis_decode_responses: bool = True,
        tls_verify: bool = False,
        ca_bundle_path: str | None = None,
        ttl: CacheTTL = CacheTTL.COOL,
    ):
        super().__init__(
            prefix=prefix,
            ssm_client=ssm_client,
            secrets_client=secrets_client,
            redis_decode_responses=redis_decode_responses,
            tls_verify=tls_verify,
            ca_bundle_path=ca_bundle_path,
        )
        self.ttl = ttl

    @handle_redis_connection_error
    def latest(self, pull: bool = True, force: bool = False) -> AppConfig:
        return self.get('latest', pull=pull, force=force)

    @handle_redis_connection_error
    def version(self, pull: bool = True, force: bool = False) -> int:
        """Version number of the latest AppConfig document."""
        return self.metadata('latest', pull=pull, force=force)['version']

    @handle_redis_connection_error
    def get(self, version: int | str, pull: bool = True, force: bool = False) -> AppConfig:
        # FORCE PULL: always fetch the document from AppConfig and cache
        if force:
            _, document, _ = self._pull_appconfig(version)
            return document

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
    def metadata(self, version: int | str, pull: bool = True, force: bool = False) -> AppConfigMetadata:
        # FORCE PULL: always fetch the metadata from AppConfig and cache
        if force:
            _, _, metadata = self._pull_appconfig(version)
            return metadata

        if version == 'latest':
            key = self.keys.appconfig_latest_metadata_key()
        else:
            key = self.keys.appconfig_metadata_key(int(version))
        appconfig_metadata_blob = self.redis.get(key)

        # CACHE HIT: load appconfig metadata as deserialized JSON object (Python dictionary)
        if appconfig_metadata_blob is not None:
            return json.loads(appconfig_metadata_blob)

        # CACHE MISS: raise CacheMissError if pull=False
        #             otherwise fetch the metadata from AppConfig
        if not pull:
            raise CacheMissError(f'AppConfig v{version} metadata not found in cache and pull=False.')

        _, _, metadata = self._pull_appconfig(version)
        return metadata

    def _pull_appconfig(self, version: int | str) -> tuple[int, AppConfig, AppConfigMetadata]:
        """Fetch the requested AppConfig document + metadata and warm the cache.

        Behavior:
            - If version == 'latest', uses the AppConfig Data API and writes:
              * <prefix>:appconfig:v{resolved_version}
              * <prefix>:appconfig:v{resolved_version}:metadata
              * <prefix>:appconfig:latest (duplicate of document, for faster HITs)
              * <prefix>:appconfig:latest:metadata (duplicate of metadata, for faster HITs)
            - If version is an int, uses the AppConfig control-plane API to fetch
              the specific hosted configuration version and writes the versioned keys.
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

    def _warm_up_cache(
        self,
        resolved_version: int,
        document: AppConfig,
        metadata: AppConfigMetadata,
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
                if latest:  # duplicate AppConfig document & metadata for faster retrieval
                    pipe.set(latest_key, document_json, ex=self.ttl)
                    pipe.set(latest_meta_key, metadata_json, ex=self.ttl)
                pipe.execute()
        except redis.exceptions.ConnectionError as e:
            raise CachePutError(
                f'Failed to write AppConfig v{resolved_version} to cache. '
                '(hint: you may be using the read-only replica, ensure you are using the master)'
            ) from e

    @require_environment(ENV.AppConfig.APP_ID, ENV.AppConfig.ENV_ID, ENV.AppConfig.PROFILE_ID)
    def _fetch_latest_appconfig(self) -> tuple[int, AppConfig, AppConfigMetadata]:
        """Fetch the latest AppConfig document via the AppConfig Data API.

        Raises:
            ValueError:
                TODO: turn this into a custom exception.
                If required environment variables are missing, the response lacks a
                configuration version header, or the version header is invalid.
        """
        app_id = os.environ[ENV.AppConfig.APP_ID]
        env_id = os.environ[ENV.AppConfig.ENV_ID]
        profile_id = os.environ[ENV.AppConfig.PROFILE_ID]

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
        # Try multiple possible header names for version information
        headers = resp.get('ResponseMetadata', {}).get('HTTPHeaders', {})
        version_str = (
            headers.get('configuration-version')
            or headers.get('x-amzn-appconfig-configuration-version')
            or headers.get('Version-Label')
            or headers.get('version-label')
        )

        # If version is not in headers, fetch it from the control-plane API
        if not version_str:
            resolved_version = self._get_latest_version_number()
        else:
            try:
                resolved_version = int(version_str)
            except (TypeError, ValueError) as e:
                raise AppConfigError(f'Invalid configuration-version header: {version_str!r}') from e

        metadata = {
            'version': resolved_version,
            'etag': headers.get('etag'),
            'content_type': resp.get('ContentType'),
            'fetched_at': datetime.now(UTC).isoformat(),
        }
        return resolved_version, document, metadata

    @require_environment(ENV.AppConfig.APP_ID, ENV.AppConfig.PROFILE_ID)
    def _get_latest_version_number(self) -> int:
        """Get the latest hosted configuration version number from the control-plane API.

        This method is used as a fallback when the Data API doesn't return version
        information in headers.
        """
        app_id = os.environ[ENV.AppConfig.APP_ID]
        profile_id = os.environ[ENV.AppConfig.PROFILE_ID]

        # Use control-plane API to list hosted configuration versions
        # Get the latest version (first result when sorted descending)
        client = boto3.client('appconfig')
        try:
            response = client.list_hosted_configuration_versions(
                ApplicationId=app_id,
                ConfigurationProfileId=profile_id,
                MaxResults=1,
            )
            versions = response.get('Items', [])
            if not versions:
                raise AppConfigError('No hosted configuration versions found for this profile.')
            # Versions are returned in descending order by default, so first is latest
            latest_version = versions[0].get('VersionNumber')
            if latest_version is None:
                raise AppConfigError('Latest configuration version missing VersionNumber field.')
            return int(latest_version)
        except (KeyError, TypeError, ValueError) as e:
            raise AppConfigError(f'Failed to determine latest configuration version: {e}') from e

    @require_environment(ENV.AppConfig.APP_ID, ENV.AppConfig.PROFILE_ID)
    def _fetch_appconfig(self, version: int) -> tuple[int, AppConfig, AppConfigMetadata]:
        """Fetch a specific hosted AppConfig version via the control-plane API."""
        app_id = os.environ[ENV.AppConfig.APP_ID]
        profile_id = os.environ[ENV.AppConfig.PROFILE_ID]

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
        etag = resp.get('ResponseMetadata', {}).get('HTTPHeaders', {}).get('etag')
        metadata = {
            'version': version,
            'etag': etag,
            'content_type': resp.get('ContentType'),
            'fetched_at': datetime.now(UTC).isoformat(),
        }
        return version, document, metadata
