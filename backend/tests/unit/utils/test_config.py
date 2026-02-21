"""Unit tests for configuration utilities in config.py."""

import json
from io import BytesIO
from typing import cast
from unittest.mock import MagicMock

import pytest
from botocore.exceptions import ClientError
from pytest import MonkeyPatch

from cloudshortener.types import AppConfig
from cloudshortener.utils import config
from cloudshortener.constants import ENV
from cloudshortener.dao.exceptions import CacheMissError
from cloudshortener.dao.cache import AppConfigCacheDAO


class TestConfigUtilities:
    appconfig_payload: AppConfig
    healthy_cache_dao: AppConfigCacheDAO
    failing_cache_dao: AppConfigCacheDAO

    @pytest.fixture
    def appconfig_payload(self) -> AppConfig:
        # fmt: off
        return cast(AppConfig, {
            'build': 42,
            'active_backend': 'redis',
            'configs': {
                'test_lambda': {
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
    def healthy_cache_dao(self, appconfig_payload: AppConfig) -> AppConfigCacheDAO:
        inst = MagicMock(spec=AppConfigCacheDAO)
        inst.latest.return_value = appconfig_payload
        return inst

    @pytest.fixture
    def failing_cache_dao(self) -> AppConfigCacheDAO:
        inst = MagicMock(spec=AppConfigCacheDAO)
        inst.latest.side_effect = CacheMissError('cache miss')
        return inst

    @pytest.fixture(autouse=True)
    def setup(self, monkeypatch: MonkeyPatch, appconfig_payload: AppConfig) -> None:
        monkeypatch.setenv(ENV.AppConfig.APP_ID, 'app123')
        monkeypatch.setenv(ENV.AppConfig.ENV_ID, 'env123')
        monkeypatch.setenv(ENV.AppConfig.PROFILE_ID, 'prof123')
        monkeypatch.setattr(config, 'app_prefix', lambda: 'test-app:test')

        self.appconfig_payload = appconfig_payload

    def test_load_config_uses_fallback_when_cache_misses(
        self,
        monkeypatch: MonkeyPatch,
        failing_cache_dao: AppConfigCacheDAO,
    ) -> None:
        """Ensure load_config() falls back to direct AppConfig when cache path fails.

        The AppConfigCacheDAO.latest() call raises CacheMissError, causing the decorator
        to delegate to the original AppConfig-based implementation, which is then mocked
        via boto3.client.
        """
        # Patch AppConfigCacheDAO to return a failing instance
        import cloudshortener.dao.cache as cache_module

        monkeypatch.setattr(cache_module, 'AppConfigCacheDAO', MagicMock(return_value=failing_cache_dao))

        # Mock AppConfig Data client (fallback path)
        monkey_bytes = BytesIO(json.dumps(self.appconfig_payload).encode('utf-8'))
        mock_appconfig = MagicMock()
        mock_appconfig.start_configuration_session.return_value = {'InitialConfigurationToken': 'monkey_token'}
        mock_appconfig.get_latest_configuration.return_value = {'Configuration': monkey_bytes}
        monkeypatch.setattr(config.boto3, 'client', lambda service: mock_appconfig)

        result = config.load_config('test_lambda')

        # Result should match payload structure
        assert result['redis']['host'] == 'monkey'
        assert result['redis']['port'] == 659595
        assert result['redis']['db'] == 3

        # Cache DAO was used first
        cache_module.AppConfigCacheDAO.assert_called_once_with(prefix='test-app:test')
        failing_cache_dao.latest.assert_called_once_with(pull=True)

        # Fallback AppConfig calls were made
        mock_appconfig.start_configuration_session.assert_called_once_with(
            ApplicationIdentifier='app123',
            EnvironmentIdentifier='env123',
            ConfigurationProfileIdentifier='prof123',
        )
        mock_appconfig.get_latest_configuration.assert_called_once_with(
            ConfigurationToken='monkey_token',
        )

    def test_missing_appconfig_raises_error(
        self,
        monkeypatch: MonkeyPatch,
        failing_cache_dao: AppConfigCacheDAO,
    ) -> None:
        """Ensure load_config() propagates ClientError when AppConfig returns an error.

        The cache path fails (CacheMissError), and the underlying AppConfig call
        is simulated to raise ClientError.
        """
        import cloudshortener.dao.cache as cache_module

        monkeypatch.setattr(cache_module, 'AppConfigCacheDAO', MagicMock(return_value=failing_cache_dao))

        mock_appconfig = MagicMock()
        mock_appconfig.start_configuration_session.side_effect = ClientError(
            {'Error': {'Code': 'ResourceNotFoundException'}}, 'StartConfigurationSession'
        )
        monkeypatch.setattr(config.boto3, 'client', lambda service: mock_appconfig)

        with pytest.raises(ClientError):
            config.load_config('test_lambda')

        cache_module.AppConfigCacheDAO.assert_called_once_with(prefix='test-app:test')
        failing_cache_dao.latest.assert_called_once_with(pull=True)

    def test_load_config_uses_cache_when_available(
        self,
        monkeypatch: MonkeyPatch,
        healthy_cache_dao: AppConfigCacheDAO,
    ) -> None:
        """Ensure load_config() uses AppConfigCacheDAO when cache is available.

        In this scenario, the cache path succeeds and the underlying AppConfig
        client must not be called.
        """
        import cloudshortener.dao.cache as cache_module

        monkeypatch.setattr(cache_module, 'AppConfigCacheDAO', MagicMock(return_value=healthy_cache_dao))

        # Mock AppConfig Data client but ensure it's never used
        mock_appconfig = MagicMock()
        monkeypatch.setattr(config.boto3, 'client', lambda service: mock_appconfig)

        result = config.load_config('test_lambda')

        # Result should come from cached document
        assert result['redis']['host'] == self.appconfig_payload['configs']['test_lambda']['redis']['host']
        assert result['redis']['port'] == self.appconfig_payload['configs']['test_lambda']['redis']['port']
        assert result['redis']['db'] == self.appconfig_payload['configs']['test_lambda']['redis']['db']

        cache_module.AppConfigCacheDAO.assert_called_once_with(prefix='test-app:test')
        healthy_cache_dao.latest.assert_called_once_with(pull=True)

        mock_appconfig.start_configuration_session.assert_not_called()
        mock_appconfig.get_latest_configuration.assert_not_called()
