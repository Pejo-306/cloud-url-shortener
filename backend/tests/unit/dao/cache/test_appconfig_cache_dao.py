import json
from io import BytesIO
from typing import cast
from unittest.mock import MagicMock, call

import pytest
import redis
from pytest import MonkeyPatch
from freezegun import freeze_time

from cloudshortener.types import AppConfig, AppConfigMetadata, AppConfigDataClient, AppConfigClient
from cloudshortener.dao.cache.cache_key_schema import CacheKeySchema
from cloudshortener.dao.cache.appconfig_cache_dao import AppConfigCacheDAO
from cloudshortener.dao.exceptions import CacheMissError, CachePutError
from cloudshortener.exceptions import MissingEnvironmentVariableError
from cloudshortener.constants import ENV


from cloudshortener.dao.cache.constants import CacheTTL


class TestAppConfigCacheDAO:
    app_prefix: str
    default_appconfig_doc: AppConfig
    default_appconfig_metadata: AppConfigMetadata
    appconfigdata_client: AppConfigDataClient
    appconfig_client: AppConfigClient
    dao: AppConfigCacheDAO
    redis_client: redis.Redis

    @pytest.fixture(autouse=True)
    def _env(self, monkeypatch: MonkeyPatch) -> None:
        monkeypatch.setenv(ENV.AppConfig.APP_ID, 'app123')
        monkeypatch.setenv(ENV.AppConfig.ENV_ID, 'env123')
        monkeypatch.setenv(ENV.AppConfig.PROFILE_ID, 'prof123')

    @pytest.fixture
    def default_appconfig_doc(self) -> AppConfig:
        return cast(
            AppConfig,
            {
                'active_backend': 'redis',
                'configs': {
                    'shorten_url': {
                        'redis': {
                            'host': 'localtest',
                            'port': 96379,
                            'db': 42,
                        }
                    },
                    'redirect_url': {
                        'redis': {
                            'host': 'localtest',
                            'port': 66379,
                            'db': 24,
                        }
                    },
                },
            },
        )

    @pytest.fixture
    def default_appconfig_metadata(self) -> AppConfigMetadata:
        return cast(
            AppConfigMetadata,
            {
                'version': 42,
                'etag': 'W/"etag-latest"',
                'content_type': 'application/json',
                'fetched_at': '2025-01-03T00:00:00+00:00',
            },
        )

    @pytest.fixture
    def appconfigdata_client(
        self,
        default_appconfig_doc: AppConfig,
        default_appconfig_metadata: AppConfigMetadata,
    ) -> AppConfigDataClient:
        client = MagicMock()
        client.start_configuration_session.return_value = {'InitialConfigurationToken': 'token-xyz'}
        client.get_latest_configuration.return_value = {
            'Configuration': BytesIO(json.dumps(default_appconfig_doc).encode('utf-8')),
            'ContentType': 'application/json',
            'ResponseMetadata': {
                'HTTPHeaders': {
                    'configuration-version': str(default_appconfig_metadata['version']),
                    'etag': default_appconfig_metadata['etag'],
                },
            },
        }
        return client

    @pytest.fixture
    def appconfig_client(
        self,
        default_appconfig_doc: AppConfig,
        default_appconfig_metadata: AppConfigMetadata,
    ) -> AppConfigClient:
        client = MagicMock()
        client.get_hosted_configuration_version.return_value = {
            'Content': BytesIO(json.dumps(default_appconfig_doc).encode('utf-8')),
            'ContentType': 'application/json',
            'ResponseMetadata': {
                'HTTPHeaders': {
                    'configuration-version': str(default_appconfig_metadata['version']),
                    'etag': default_appconfig_metadata['etag'],
                },
            },
        }
        return client

    @pytest.fixture(autouse=True)
    def boto3_client(
        self,
        monkeypatch: MonkeyPatch,
        appconfigdata_client: AppConfigDataClient,
        appconfig_client: AppConfigClient,
    ) -> None:
        import boto3 as _boto3

        def _client(service_name: str, *args, **kwargs):
            if service_name == 'appconfigdata':
                return appconfigdata_client
            if service_name == 'appconfig':
                return appconfig_client
            raise AssertionError(f'Unexpected boto3 client requested: {service_name}')

        monkeypatch.setattr(_boto3, 'client', _client)

    @pytest.fixture
    def dao(self, redis_client: redis.Redis, app_prefix: str) -> AppConfigCacheDAO:
        _dao = object.__new__(AppConfigCacheDAO)
        _dao.redis = redis_client
        _dao.keys = CacheKeySchema(prefix=app_prefix)
        _dao.ttl = CacheTTL.COOL
        return _dao

    @pytest.fixture(autouse=True)
    def setup(self, dao: AppConfigCacheDAO, redis_client: redis.Redis) -> None:
        self.dao = dao
        self.redis_client = redis_client

    def test_latest_cache_hit_returns_document(self, default_appconfig_doc: AppConfig):
        self.redis_client.get.return_value = json.dumps(default_appconfig_doc)

        result = self.dao.latest(pull=False)

        assert isinstance(result, dict)
        assert result['active_backend'] == 'redis'
        assert result['configs']['shorten_url']['redis']['host'] == 'localtest'
        assert result['configs']['shorten_url']['redis']['port'] == 96379
        assert result['configs']['shorten_url']['redis']['db'] == 42
        assert result['configs']['redirect_url']['redis']['host'] == 'localtest'
        assert result['configs']['redirect_url']['redis']['port'] == 66379
        assert result['configs']['redirect_url']['redis']['db'] == 24

        self.redis_client.get.assert_called_once_with('cache:testapp:test:appconfig:latest')

    def test_latest_cache_miss_with_pull_false_raises(self):
        self.redis_client.get.return_value = None
        with pytest.raises(CacheMissError, match='latest'):
            self.dao.latest(pull=False)

    @freeze_time('2025-01-03T00:00:00Z')
    def test_latest_cache_miss_with_pull_true_fetches_and_writes(
        self,
        default_appconfig_doc: AppConfig,
        default_appconfig_metadata: AppConfigMetadata,
    ):
        # fmt: off
        expected_calls = [
            call('cache:testapp:test:appconfig:v42', json.dumps(default_appconfig_doc, separators=(',', ':'), ensure_ascii=False), ex=CacheTTL.COOL),
            call('cache:testapp:test:appconfig:v42:metadata', json.dumps(default_appconfig_metadata, separators=(',', ':'), ensure_ascii=False), ex=CacheTTL.COOL),
            call('cache:testapp:test:appconfig:latest', json.dumps(default_appconfig_doc, separators=(',', ':'), ensure_ascii=False), ex=CacheTTL.COOL),
            call('cache:testapp:test:appconfig:latest:metadata', json.dumps(default_appconfig_metadata, separators=(',', ':'), ensure_ascii=False), ex=CacheTTL.COOL),
        ]
        # fmt: on
        self.redis_client.get.return_value = None

        result = self.dao.latest(pull=True)

        assert isinstance(result, dict)
        assert result['active_backend'] == 'redis'
        assert result['configs']['shorten_url']['redis']['host'] == 'localtest'
        assert result['configs']['shorten_url']['redis']['port'] == 96379
        assert result['configs']['shorten_url']['redis']['db'] == 42
        assert result['configs']['redirect_url']['redis']['host'] == 'localtest'
        assert result['configs']['redirect_url']['redis']['port'] == 66379
        assert result['configs']['redirect_url']['redis']['db'] == 24

        assert self.redis_client.set.call_count == 4
        self.redis_client.set.assert_has_calls(expected_calls)
        self.redis_client.execute.assert_called_once()

    def test_get_version_cache_hit_returns_document(self, default_appconfig_doc: AppConfig):
        self.redis_client.get.return_value = json.dumps(default_appconfig_doc)

        result = self.dao.get(42, pull=False)

        assert isinstance(result, dict)
        assert result['active_backend'] == 'redis'
        assert result['configs']['shorten_url']['redis']['host'] == 'localtest'
        assert result['configs']['shorten_url']['redis']['port'] == 96379
        assert result['configs']['shorten_url']['redis']['db'] == 42
        assert result['configs']['redirect_url']['redis']['host'] == 'localtest'
        assert result['configs']['redirect_url']['redis']['port'] == 66379
        assert result['configs']['redirect_url']['redis']['db'] == 24

        self.redis_client.get.assert_called_once_with('cache:testapp:test:appconfig:v42')

    def test_get_version_cache_miss_with_pull_false_raises(self):
        self.redis_client.get.return_value = None
        with pytest.raises(CacheMissError, match='v42'):
            self.dao.get(42, pull=False)

    @freeze_time('2025-01-03T00:00:00Z')
    def test_get_version_cache_miss_with_pull_true_fetches_and_writes(
        self,
        default_appconfig_doc: AppConfig,
        default_appconfig_metadata: AppConfigMetadata,
    ):
        written_appconfig_metadata = default_appconfig_metadata.copy()
        written_appconfig_metadata['version'] = 9
        # fmt: off
        expected_calls = [
            call('cache:testapp:test:appconfig:v9', json.dumps(default_appconfig_doc, separators=(',', ':'), ensure_ascii=False), ex=CacheTTL.COOL),
            call('cache:testapp:test:appconfig:v9:metadata', json.dumps(written_appconfig_metadata, separators=(',', ':'), ensure_ascii=False), ex=CacheTTL.COOL),
        ]
        # fmt: on
        self.redis_client.get.return_value = None

        result = self.dao.get(9, pull=True)

        assert isinstance(result, dict)
        assert result['active_backend'] == 'redis'
        assert result['configs']['shorten_url']['redis']['host'] == 'localtest'
        assert result['configs']['shorten_url']['redis']['port'] == 96379
        assert result['configs']['shorten_url']['redis']['db'] == 42
        assert result['configs']['redirect_url']['redis']['host'] == 'localtest'
        assert result['configs']['redirect_url']['redis']['port'] == 66379
        assert result['configs']['redirect_url']['redis']['db'] == 24

        assert self.redis_client.set.call_count == 2
        self.redis_client.set.assert_has_calls(expected_calls)
        self.redis_client.execute.assert_called_once()

    def test_metadata_cache_hit_returns_metadata(self, default_appconfig_metadata):
        self.redis_client.get.return_value = json.dumps(default_appconfig_metadata)

        result = self.dao.metadata(42, pull=False)

        assert isinstance(result, dict)
        assert result['version'] == 42
        assert result['etag'] == 'W/"etag-latest"'
        assert result['content_type'] == 'application/json'
        assert result['fetched_at'] == '2025-01-03T00:00:00+00:00'

        self.redis_client.get.assert_called_once_with('cache:testapp:test:appconfig:v42:metadata')

    def test_metadata_cache_miss_with_pull_false_raises(self):
        self.redis_client.get.return_value = None
        with pytest.raises(CacheMissError, match='metadata'):
            self.dao.metadata(11, pull=False)

    @freeze_time('2025-01-03T00:00:00Z')
    def test_metadata_cache_miss_with_pull_true_fetches_and_writes(
        self,
        default_appconfig_doc: AppConfig,
        default_appconfig_metadata: AppConfigMetadata,
    ):
        written_appconfig_metadata = default_appconfig_metadata.copy()
        written_appconfig_metadata['version'] = 9
        # fmt: off
        expected_calls = [
            call('cache:testapp:test:appconfig:v9', json.dumps(default_appconfig_doc, separators=(',', ':'), ensure_ascii=False), ex=CacheTTL.COOL),
            call('cache:testapp:test:appconfig:v9:metadata', json.dumps(written_appconfig_metadata, separators=(',', ':'), ensure_ascii=False), ex=CacheTTL.COOL),
        ]
        # fmt: on
        self.redis_client.get.return_value = None

        result = self.dao.metadata(9, pull=True)

        assert isinstance(result, dict)
        assert result['version'] == 9
        assert result['etag'] == 'W/"etag-latest"'
        assert result['content_type'] == 'application/json'
        assert result['fetched_at'] == '2025-01-03T00:00:00+00:00'

        assert self.redis_client.set.call_count == 2
        self.redis_client.set.assert_has_calls(expected_calls)
        self.redis_client.execute.assert_called_once()

    def test_version_cache_hit_returns_version(self, default_appconfig_metadata: AppConfigMetadata):
        self.redis_client.get.return_value = json.dumps(default_appconfig_metadata)

        result = self.dao.version(pull=False)
        assert result == 42

        self.redis_client.get.assert_called_once_with('cache:testapp:test:appconfig:latest:metadata')

    def test_version_cache_miss_with_pull_false_raises(self):
        self.redis_client.get.return_value = None
        with pytest.raises(CacheMissError, match='latest'):
            self.dao.version(pull=False)

    @freeze_time('2025-01-03T00:00:00Z')
    def test_version_cache_miss_with_pull_true_fetches_and_writes(
        self,
        default_appconfig_doc: AppConfig,
        default_appconfig_metadata: AppConfigMetadata,
    ):
        # fmt: off
        expected_calls = [
            call('cache:testapp:test:appconfig:v42', json.dumps(default_appconfig_doc, separators=(',', ':'), ensure_ascii=False), ex=CacheTTL.COOL),
            call('cache:testapp:test:appconfig:v42:metadata', json.dumps(default_appconfig_metadata, separators=(',', ':'), ensure_ascii=False), ex=CacheTTL.COOL),
            call('cache:testapp:test:appconfig:latest', json.dumps(default_appconfig_doc, separators=(',', ':'), ensure_ascii=False), ex=CacheTTL.COOL),
            call('cache:testapp:test:appconfig:latest:metadata', json.dumps(default_appconfig_metadata, separators=(',', ':'), ensure_ascii=False), ex=CacheTTL.COOL),
        ]
        # fmt: on
        self.redis_client.get.return_value = None

        result = self.dao.version(pull=True)
        assert result == 42

        assert self.redis_client.set.call_count == 4
        self.redis_client.set.assert_has_calls(expected_calls)
        self.redis_client.execute.assert_called_once()

    def test_cache_put_error_when_pipeline_execute_fails(self):
        self.redis_client.get.return_value = None
        self.redis_client.execute.side_effect = redis.exceptions.ConnectionError('Connection error')

        with pytest.raises(CachePutError, match='Failed to write AppConfig v42'):
            self.dao.get(42, pull=True)

    def test_fetch_latest_env_validation_missing_vars(self, monkeypatch: MonkeyPatch):
        monkeypatch.delenv(ENV.AppConfig.ENV_ID, raising=False)
        expected_message = "Missing required environment variables: 'APPCONFIG_ENV_ID'"
        with pytest.raises(MissingEnvironmentVariableError, match=expected_message):
            self.dao.latest(pull=True)

    def test_fetch_version_env_validation_missing_vars(self, monkeypatch: MonkeyPatch):
        monkeypatch.delenv(ENV.AppConfig.PROFILE_ID, raising=False)
        expected_message = "Missing required environment variables: 'APPCONFIG_PROFILE_ID'"
        with pytest.raises(MissingEnvironmentVariableError, match=expected_message):
            self.dao.get(42, pull=True)

    @freeze_time('2025-01-03T00:00:00Z')
    def test_force_pull_latest(
        self,
        default_appconfig_doc: AppConfig,
        default_appconfig_metadata: AppConfigMetadata,
    ):
        self.redis_client.get.return_value = json.dumps({'stale': 'data'})

        # fmt: off
        expected_calls = [
            call('cache:testapp:test:appconfig:v42', json.dumps(default_appconfig_doc, separators=(',', ':'), ensure_ascii=False), ex=CacheTTL.COOL),
            call('cache:testapp:test:appconfig:v42:metadata', json.dumps(default_appconfig_metadata, separators=(',', ':'), ensure_ascii=False), ex=CacheTTL.COOL),
            call('cache:testapp:test:appconfig:latest', json.dumps(default_appconfig_doc, separators=(',', ':'), ensure_ascii=False), ex=CacheTTL.COOL),
            call('cache:testapp:test:appconfig:latest:metadata', json.dumps(default_appconfig_metadata, separators=(',', ':'), ensure_ascii=False), ex=CacheTTL.COOL),
        ]
        # fmt: on

        result = self.dao.latest(force=True)

        assert isinstance(result, dict)
        assert result == default_appconfig_doc
        assert result['active_backend'] == 'redis'
        assert result['configs']['shorten_url']['redis']['host'] == 'localtest'
        assert result['configs']['shorten_url']['redis']['port'] == 96379
        assert result['configs']['shorten_url']['redis']['db'] == 42
        assert result['configs']['redirect_url']['redis']['host'] == 'localtest'
        assert result['configs']['redirect_url']['redis']['port'] == 66379
        assert result['configs']['redirect_url']['redis']['db'] == 24

        self.redis_client.get.assert_not_called()

        assert self.redis_client.set.call_count == 4
        self.redis_client.set.assert_has_calls(expected_calls)
        self.redis_client.execute.assert_called_once()
