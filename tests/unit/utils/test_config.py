"""Unit tests for configuration utilities in config.py

Test coverage includes:

1. Environment variable resolution
   - Ensures app_env() and app_name() correctly read environment variables.

2. Project root resolution
   - Ensures project_root() correctly reads PROJECT_ROOT from environment variables.

3. Configuration loading behavior
   - Ensures load_config() correctly returns parsed YAML configuration data.
   - Validates that filesystem and YAML parsing are safely isolated via monkeypatching.
   - Ensures load_config() raises FileNotFoundError when YAML configuration files are missing.
"""

import builtins
import os
from io import StringIO

import pytest

from cloudshortener.utils import config
from pathlib import Path


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
    monkey_config = {
        'redis': {
            'host': 'monkey',
            'port': 659595,
            'db': 3,
        }
    }

    # Mock builtins.open to prevent file I/O
    monkeypatch.setattr(builtins, 'open', lambda *a, **kw: StringIO("FAKENESS"))

    # Mock yaml.safe_load to return fake configuration
    monkeypatch.setattr(config.yaml, 'safe_load', lambda f: monkey_config)

    # Mock Path.exists to bypass file existence checks
    monkeypatch.setattr(config.Path, 'exists', lambda self: True)

    result = config.load_config('test_lambda')

    assert result['redis']['host'] == 'monkey'
    assert result['redis']['port'] == 659595
    assert result['redis']['db'] == 3


def test_missing_file_raises_error(monkeypatch):
    """Ensure load_config() raises FileNotFoundError when configuration files are missing"""
    # Mock Path.exists to bypass file existence checks
    monkeypatch.setattr(config.Path, 'exists', lambda self: False)

    with pytest.raises(FileNotFoundError):
        config.load_config('test_lambda')
