"""Unit tests for configuration utilities in config.py

Test coverage includes:

1. Environment variable resolution
   - Ensures app_env(), app_name(), app_prefix() correctly read environment variables.

2. Project root resolution
   - Ensures project_root() correctly reads PROJECT_ROOT from environment variables.

3. Configuration loading behavior
   - Ensures load_config() correctly returns parsed AppConfig configuration data.
   - Validates that AppConfig fetching is safely isolated via monkeypatching.
   - Ensures load_config() raises ClientError when AppConfig calls fail.
   - Ensures cache_appconfig decorator integrates with AppConfigCacheDAO and
     falls back correctly when the cache path fails.
"""

import os
import json
from io import BytesIO
from pathlib import Path
from unittest.mock import MagicMock

import pytest
import botocore

from cloudshortener.utils import config
from cloudshortener.dao.exceptions import CacheMissError


# -------------------------------
# Fixtures
# -------------------------------


@pytest.fixture(autouse=True)
def _env(monkeypatch):
    """Set up environment variables for testing."""
    monkeypatch.setenv('APPCONFIG_APP_ID', 'app123')
    monkeypatch.setenv('APPCONFIG_ENV_ID', 'env123')
    monkeypatch.setenv('APPCONFIG_PROFILE_ID', 'prof123')


@pytest.fixture(autouse=True)
def _app_prefix(monkeypatch):
    """Ensure app_prefix() returns a deterministic value for tests."""
    monkeypatch.setattr(config, 'app_prefix', lambda: 'test-app:test')


@pytest.fixture
def appconfig_payload():
    """Provide a default AppConfig payload used by multiple tests."""
    # fmt: off
    return {
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
    }
    # fmt: on


@pytest.fixture
def healthy_cache_dao(appconfig_payload):
    """Mock an AppConfigCacheDAO instance that returns a valid cached document."""
    inst = MagicMock()
    inst.latest.return_value = appconfig_payload
    return inst


@pytest.fixture
def failing_cache_dao():
    """Mock an AppConfigCacheDAO instance that always fails with CacheMissError."""
    inst = MagicMock()
    inst.latest.side_effect = CacheMissError('cache miss')
    return inst


# -------------------------------
# 1. Environment variable resolution
# -------------------------------


def test_app_env(monkeypatch):
    """Ensure app_env() returns the correct environment value from APP_ENV"""
    monkeypatch.setitem(os.environ, 'APP_ENV', 'test')
    assert config.app_env() == 'test'


def test_app_name(monkeypatch):
    """Ensure app_name() returns the correct environment value from APP_NAME"""
    monkeypatch.setitem(os.environ, 'APP_NAME', 'test-app')
    assert config.app_name() == 'test-app'


def test_app_name_not_set(monkeypatch):
    """Ensure app_name() returns None when APP_NAME is not set"""
    monkeypatch.delitem(os.environ, 'APP_NAME', raising=False)
    assert config.app_name() is None


def test_app_prefix(monkeypatch):
    """Ensure app_prefix() returns the correct environment value from APP_PREFIX"""
    monkeypatch.setitem(os.environ, 'APP_NAME', 'test-app')
    monkeypatch.setitem(os.environ, 'APP_ENV', 'test')
    assert config.app_prefix() == 'test-app:test'


# -------------------------------
# 2. Project root resolution
# -------------------------------


def test_project_root(monkeypatch):
    """Ensure project_root() returns the corrent environment value from PROJECT_ROOT"""
    monkeypatch.setitem(os.environ, 'PROJECT_ROOT', '/monkey/path')
    assert config.project_root() == Path('/monkey/path')


# -------------------------------
# 3. Configuration loading behavior
# -------------------------------


def test_load_config_uses_fallback_when_cache_misses(monkeypatch, failing_cache_dao, appconfig_payload):
    """Ensure load_config() falls back to direct AppConfig when cache path fails.

    The AppConfigCacheDAO.latest() call raises CacheMissError, causing the decorator
    to delegate to the original AppConfig-based implementation, which is then mocked
    via boto3.client.
    """
    # Patch AppConfigCacheDAO to return a failing instance
    import cloudshortener.dao.cache as cache_module

    monkeypatch.setattr(cache_module, 'AppConfigCacheDAO', MagicMock(return_value=failing_cache_dao))

    # Mock AppConfig Data client (fallback path)
    monkey_bytes = BytesIO(json.dumps(appconfig_payload).encode('utf-8'))
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


def test_missing_appconfig_raises_error(monkeypatch, failing_cache_dao):
    """Ensure load_config() propagates ClientError when AppConfig returns an error.

    The cache path fails (CacheMissError), and the underlying AppConfig call
    is simulated to raise ClientError.
    """
    import cloudshortener.dao.cache as cache_module

    monkeypatch.setattr(cache_module, 'AppConfigCacheDAO', MagicMock(return_value=failing_cache_dao))

    mock_appconfig = MagicMock()
    mock_appconfig.start_configuration_session.side_effect = botocore.exceptions.ClientError(
        {'Error': {'Code': 'ResourceNotFoundException'}}, 'StartConfigurationSession'
    )
    monkeypatch.setattr(config.boto3, 'client', lambda service: mock_appconfig)

    with pytest.raises(botocore.exceptions.ClientError):
        config.load_config('test_lambda')

    cache_module.AppConfigCacheDAO.assert_called_once_with(prefix='test-app:test')
    failing_cache_dao.latest.assert_called_once_with(pull=True)


def test_load_config_uses_cache_when_available(monkeypatch, healthy_cache_dao, appconfig_payload):
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
    assert result['redis']['host'] == appconfig_payload['configs']['test_lambda']['redis']['host']
    assert result['redis']['port'] == appconfig_payload['configs']['test_lambda']['redis']['port']
    assert result['redis']['db'] == appconfig_payload['configs']['test_lambda']['redis']['db']

    cache_module.AppConfigCacheDAO.assert_called_once_with(prefix='test-app:test')
    healthy_cache_dao.latest.assert_called_once_with(pull=True)

    mock_appconfig.start_configuration_session.assert_not_called()
    mock_appconfig.get_latest_configuration.assert_not_called()
