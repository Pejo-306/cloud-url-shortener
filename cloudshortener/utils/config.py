"""Utility functions for environment-based YAML configuration files

This module provides a standardized way for Lambda functions to locate and
load environment-specific YAML configuration files. The configuration
directory structure is expected to follow this convention:

    config/
    ├── {lambda_name}/
    │   ├── {environment_name}.yml
    │   └── {environment_name}.yml
    ├── shorten_url/
    │   ├── local.yml
    │   └── dev.yml
    └── redirect_url/
        ├── local.yml
        └── dev.yml

Responsibilities:
    - Detect the current application environment (`APP_ENV`) from environment variables.
    - Resolve the correct configuration file path based on the Lambda name and environment.
    - Load and parse YAML configuration files into Python dictionaries.
    - Provide clear error messages when configuration files are missing.

Functions:
    app_env() -> str
        Return the current application environment (`APP_ENV`) value, defaulting to `'local'`.

    app_name() -> str | None
        Return the current application environment (`APP_NAME`) value.
        None if variable is not set.

    app_prefix() -> str | None:
        Return application prefix for DAOs.
        None if environemnt variable 'APP_NAME' is not set.

    project_root() -> Path
        Return the absolute path to the project root directory, using the
        `PROJECT_ROOT` environment variable when available.

    load_config(lambda_name: str) -> dict
        Load and parse the YAML configuration file for the specified Lambda function
        and environment. Raises `FileNotFoundError` if the configuration file does not exist.

Example:
    Typical usage within a Lambda handler:

        >>> from cloudshortener.utils.config import load_config
        >>> config = load_config('shorten_url')

        >>> print(config['redis']['host'])
        redis

        >>> print(config['redis']['port'])
        6379

TODO:
    - Add schema validation for required configuration keys.
    - Consider caching loaded configurations to improve performance
      on subsequent invocations.
"""

import os
from pathlib import Path

import yaml


def app_env() -> str:
    """Return the current application environment by reading 'APP_ENV'

    Returns:
        str:
            Value of `APP_ENV` environment variable, `'local'` by default.

    Example:
        >>> os.environ['APP_ENV'] = 'dev'
        >>> app_env()
        'dev'
    """
    return os.environ.get("APP_ENV", "local").lower()


def app_name() -> str | None:
    """Return the current application name by reading 'APP_NAME'

    Returns:
        str:
            Value of `APP_NAME` environment variable.
            None if variable is not set.

    Example:
        >>> os.environ['APP_NAME'] = 'cloudshortener'
        >>> app_name()
        'cloudshortener'
    """
    return os.environ.get('APP_NAME')


def project_root() -> Path:
    """Return the absolute path to the project root directory

    Finds the project root via the CloudFormation environment variable PROJECT_ROOT.
    Falls back to the current file.

    Returns:
        Path:
            Absolute path to the project root directory.

    Example:
        >>> project_root()
        '/var/tasks/'
    """
    return Path(os.environ.get('PROJECT_ROOT', os.path.dirname(__file__)))


def app_prefix() -> str | None:
    """Return application prefix for DAOs
    
    Returns:
        str: app prefix as <app name>:<app env>.
             None if APP_NAME is not set.

    Example:
        >>> os.environ['APP_NAME'] = 'cloudshortener'
        >>> os.environ['APP_ENV'] = 'local'
        >>> app_prefix()
        'cloudshortener:local'
    """
    return None if app_name() is None else f'{app_name()}:{app_env()}'


def load_config(lambda_name: str) -> dict:
    """Load YAML configuration file for a given Lambda and environment.

    The file is loaded as a Python dictionary and located at path (relative to project root):

        config/{lambda_name}/{APP_ENV}.yml or config/{lambda_name}/{APP_ENV}.yaml

    Args:
        lambda_name (str):
            Name of the lambda function (e.g., 'shorten_url' or 'redirect_url').

    Returns:
        dict:
            Parsed YAML configuration as a Python dictionary.

    Raises:
        FileNotFoundError:
            If neither the `.yml` nor `.yaml` configuration file exists.

    Example:
        >>> config = load_config('shorten_url')
        >>> config['redis']['host']
        'redis'
    """
    base_path = project_root() / 'config' / lambda_name
    possible_files = [
        base_path / f'{app_env()}.yml',
        base_path / f'{app_env()}.yaml',
    ]

    for path in possible_files:
        if path.exists():
            with open(path, encoding='utf-8') as f:
                return yaml.safe_load(f)

    raise FileNotFoundError(
        f"Config file not found in {base_path}: tried {', '.join(p.name for p in possible_files)}"
    )
