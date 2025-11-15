"""Unit tests for configuration utilities in config.py

Test coverage includes:

1. Environment variable resolution
   - Ensures app_env(), app_name(), app_prefix() correctly read environment variables.

2. Project root resolution
   - Ensures project_root() correctly reads PROJECT_ROOT from environment variables.

3. Configuration loading behavior
   - Ensures load_config() correctly returns parsed YAML configuration data.
   - Validates that filesystem and YAML parsing are safely isolated via monkeypatching.
   - Ensures load_config() raises FileNotFoundError when YAML configuration files are missing.
"""

import os
import json
from io import BytesIO
from pathlib import Path
from unittest.mock import MagicMock

import pytest
import botocore

from cloudshortener.utils import config


# -------------------------------
# Fixtures
# -------------------------------


@pytest.fixture(autouse=True)
def _env(monkeypatch):
    """Set up environment variables for testing"""
    monkeypatch.setenv('APPCONFIG_APP_ID', 'app123')
    monkeypatch.setenv('APPCONFIG_ENV_ID', 'env123')
    monkeypatch.setenv('APPCONFIG_PROFILE_ID', 'prof123')


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


def test_load_config(monkeypatch):
    """Ensure load_config() loads and returns the expected configuration"""
    # fmt: off
    monkey_payload = {
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

    monkey_bytes = BytesIO(json.dumps(monkey_payload).encode('utf-8'))
    mock_appconfig = MagicMock()
    mock_appconfig.start_configuration_session.return_value = {'InitialConfigurationToken': 'monkey_token'}
    mock_appconfig.get_latest_configuration.return_value = {'Configuration': monkey_bytes}
    monkeypatch.setattr(config.boto3, 'client', lambda service: mock_appconfig)

    result = config.load_config('test_lambda')

    assert result['redis']['host'] == 'monkey'
    assert result['redis']['port'] == 659595
    assert result['redis']['db'] == 3
    mock_appconfig.start_configuration_session.assert_called_once_with(
        ApplicationIdentifier='app123',
        EnvironmentIdentifier='env123',
        ConfigurationProfileIdentifier='prof123',
    )
    mock_appconfig.get_latest_configuration.assert_called_once_with(
        ConfigurationToken='monkey_token',
    )


def test_missing_appconfig_raises_error(monkeypatch):
    """Ensure load_config() raises FileNotFoundError when configuration files are missing"""
    # Mock Path.exists to bypass file existence checks
    mock_appconfig = MagicMock()
    mock_appconfig.start_configuration_session.side_effect = botocore.exceptions.ClientError(
        {'Error': {'Code': 'ResourceNotFoundException'}}, 'StartConfigurationSession'
    )
    monkeypatch.setattr(config.boto3, 'client', lambda service: mock_appconfig)

    with pytest.raises(botocore.exceptions.ClientError):
        config.load_config('test_lambda')
