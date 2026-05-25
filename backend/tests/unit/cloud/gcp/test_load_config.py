"""Unit tests for GCP configuration utilities in config.py."""

from enum import StrEnum
import json
from typing import cast
from unittest.mock import Mock

from google.cloud import storage
import pytest
from pytest import MonkeyPatch

from cloudshortener.types import BackendConfig
from cloudshortener.constants import ENV
from cloudshortener.dao.exceptions import CacheMissError
from cloudshortener.cloud.gcp import config
from cloudshortener.cloud.gcp.dao.cache import GCPBackendConfigCacheDAO


class MockFunctionName(StrEnum):
    TEST_FUNCTION = 'test_function'


class TestGCPConfigUtilities:
    backend_config_payload: BackendConfig
    healthy_cache_dao: GCPBackendConfigCacheDAO
    failing_cache_dao: GCPBackendConfigCacheDAO

    @pytest.fixture
    def backend_config_payload(self) -> BackendConfig:
        # fmt: off
        return cast(BackendConfig, {
            'build': 42,
            'active_backend': 'redis',
            'configs': {
                'test_function': {
                    'redis': {
                        'host': 'monkey',
                        'port': 659595,
                        'db': 3
                    }
                }
            },
        })
        # fmt: on

    @pytest.fixture
    def healthy_cache_dao(self, backend_config_payload: BackendConfig) -> GCPBackendConfigCacheDAO:
        inst = Mock(spec=GCPBackendConfigCacheDAO)
        inst.latest.return_value = backend_config_payload
        return inst

    @pytest.fixture
    def failing_cache_dao(self) -> GCPBackendConfigCacheDAO:
        inst = Mock(spec=GCPBackendConfigCacheDAO)
        inst.latest.side_effect = CacheMissError('cache miss')
        return inst

    @pytest.fixture(autouse=True)
    def setup(self, monkeypatch: MonkeyPatch, backend_config_payload: BackendConfig) -> None:
        monkeypatch.setenv(ENV.GCP.CONFIG_GCS_BUCKET, 'cfg-bucket')
        monkeypatch.setattr(config, 'app_prefix', lambda: 'test-app:test')
        monkeypatch.setattr(config, 'FunctionName', MockFunctionName)

        self.backend_config_payload = backend_config_payload

    def test_load_config_uses_fallback_when_cache_misses(
        self,
        monkeypatch: MonkeyPatch,
        failing_cache_dao: GCPBackendConfigCacheDAO,
    ) -> None:
        """Ensure load_config() falls back to direct GCS when cache path fails.

        The GCPBackendConfigCacheDAO.latest() call raises CacheMissError, causing the
        decorator to delegate to the original GCS-based implementation, which is then
        mocked via storage.Client.
        """
        # Patch GCPBackendConfigCacheDAO to return a failing instance
        import cloudshortener.cloud.gcp.dao.cache as cache_module

        monkeypatch.setattr(cache_module, 'GCPBackendConfigCacheDAO', Mock(return_value=failing_cache_dao))

        # Mock GCS client (fallback path)
        mock_blob = Mock(spec=storage.Blob)
        mock_blob.download_as_text.return_value = json.dumps(self.backend_config_payload)
        mock_bucket = Mock(spec=storage.Bucket)
        mock_bucket.blob.return_value = mock_blob
        mock_storage = Mock(spec=storage.Client)
        mock_storage.bucket.return_value = mock_bucket
        monkeypatch.setattr(config.storage, 'Client', lambda: mock_storage)

        result = config.load_config(MockFunctionName.TEST_FUNCTION)

        # Result should match payload structure
        assert result['redis']['host'] == 'monkey'
        assert result['redis']['port'] == 659595
        assert result['redis']['db'] == 3

        # Cache DAO was used first
        cache_module.GCPBackendConfigCacheDAO.assert_called_once_with(prefix='test-app:test')
        failing_cache_dao.latest.assert_called_once_with(pull=True)

        # Fallback GCS calls were made
        mock_storage.bucket.assert_called_once_with('cfg-bucket')
        mock_bucket.blob.assert_called_once_with('backend-config.json')
        mock_blob.download_as_text.assert_called_once_with()

    def test_missing_gcs_object_raises_error(
        self,
        monkeypatch: MonkeyPatch,
        failing_cache_dao: GCPBackendConfigCacheDAO,
    ) -> None:
        """Ensure load_config() propagates FileNotFoundError when GCS returns an error.

        The cache path fails (CacheMissError), and the underlying GCS call
        is simulated to raise FileNotFoundError.
        """
        import cloudshortener.cloud.gcp.dao.cache as cache_module

        monkeypatch.setattr(cache_module, 'GCPBackendConfigCacheDAO', Mock(return_value=failing_cache_dao))

        mock_blob = Mock(spec=storage.Blob)
        mock_blob.download_as_text.side_effect = FileNotFoundError('backend-config.json')
        mock_bucket = Mock(spec=storage.Bucket)
        mock_bucket.blob.return_value = mock_blob
        mock_storage = Mock(spec=storage.Client)
        mock_storage.bucket.return_value = mock_bucket
        monkeypatch.setattr(config.storage, 'Client', lambda: mock_storage)

        with pytest.raises(FileNotFoundError):
            config.load_config(MockFunctionName.TEST_FUNCTION)

        cache_module.GCPBackendConfigCacheDAO.assert_called_once_with(prefix='test-app:test')
        failing_cache_dao.latest.assert_called_once_with(pull=True)

    def test_load_config_uses_cache_when_available(
        self,
        monkeypatch: MonkeyPatch,
        healthy_cache_dao: GCPBackendConfigCacheDAO,
    ) -> None:
        """Ensure load_config() uses GCPBackendConfigCacheDAO when cache is available.

        In this scenario, the cache path succeeds and the underlying GCS
        client must not be called.
        """
        import cloudshortener.cloud.gcp.dao.cache as cache_module

        monkeypatch.setattr(cache_module, 'GCPBackendConfigCacheDAO', Mock(return_value=healthy_cache_dao))

        # Mock GCS client but ensure it's never used
        mock_storage = Mock(spec=storage.Client)
        monkeypatch.setattr(config.storage, 'Client', lambda: mock_storage)

        result = config.load_config(MockFunctionName.TEST_FUNCTION)

        # Result should come from cached document
        assert result['redis']['host'] == self.backend_config_payload['configs']['test_function']['redis']['host']
        assert result['redis']['port'] == self.backend_config_payload['configs']['test_function']['redis']['port']
        assert result['redis']['db'] == self.backend_config_payload['configs']['test_function']['redis']['db']

        cache_module.GCPBackendConfigCacheDAO.assert_called_once_with(prefix='test-app:test')
        healthy_cache_dao.latest.assert_called_once_with(pull=True)

        mock_storage.bucket.assert_not_called()
