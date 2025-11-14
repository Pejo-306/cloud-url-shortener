"""Utility functions for application configuration management.

This module provides a standardized interface for Lambda functions to
access configuration data stored in **AWS AppConfig**. Each environment
(`APP_ENV`) has a dedicated AppConfig *Environment* within the shared
AppConfig *Application* identified by `APP_NAME`. Configuration data is
stored as a JSON document under a configuration profile (typically
`backend-config`) and deployed to the corresponding environment.

The configuration JSON follows this structure:

    {
        "active_backend": "redis",
        "configs": {
            "shorten_url": {
                "redis": { ... }
            },
            "redirect_url": {
                "redis": { ... }
            }
        }
    }

Each Lambda loads its own section (e.g., `"shorten_url"`) from this
AppConfig document, determined by the current application environment.

NOTE (Deprecated):
    Older versions of this project stored configuration in local YAML
    files within a `config/` directory. That mechanism is now deprecated
    in favor of centralized AppConfig management. The previous structure
    looked like this:

        config/
        ├── shorten_url/
        │   ├── local.yml
        │   └── dev.yml
        └── redirect_url/
            ├── local.yml
            └── dev.yml

Functions:
    app_env() -> str
        Return the current application environment (`APP_ENV`) value,
        defaulting to `'local'`.

    app_name() -> str | None
        Return the application name (`APP_NAME`), or None if not set.

    app_prefix() -> str | None
        Return application prefix for DAOs, or None if `APP_NAME` is not set.

    project_root() -> Path
        Return the absolute path to the project root directory, using
        `PROJECT_ROOT` when available.

    load_config(lambda_name: str) -> dict
        Load configuration for a given Lambda from AWS AppConfig and
        return it as a Python dictionary.

Example:
    Typical usage inside a Lambda handler:

        >>> from cloudshortener.utils.config import load_config
        >>> config = load_config('shorten_url')
        >>> print(config['redis']['host'])
        redis-15501.host.docker.internal

TODO:
    - Add schema validation for required configuration keys.
    - Add caching of AppConfig responses for better cold-start performance.
"""

import os
import json
from pathlib import Path

import boto3


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
    return os.environ.get('APP_ENV', 'local').lower()


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
    """Load configuration for a given Lambda from AWS AppConfig

    Fetches the AppConfig JSON once and returns the section relevant
    to the requested Lambda function (e.g., 'shorten_url', 'redirect_url').

    Environment variables required:
        APPCONFIG_APP_ID       – AppConfig Application ID
        APPCONFIG_ENV_ID       – AppConfig Environment ID
        APPCONFIG_PROFILE_ID   – AppConfig Configuration Profile ID

    Args:
        lambda_name (str):
            Name of the Lambda (e.g., "shorten_url" or "redirect_url").

    Returns:
        dict: The lambda's config section as a Python dictionary.

    Example:
        >>> app_config = load_config('shorten_url')
        >>> app_config['redis']['host']
        'redis-15501.host.docker.internal'
    """
    appconfig = boto3.client('appconfigdata')

    # Start an AppConfig data session
    session_token = appconfig.start_configuration_session(
        ApplicationIdentifier=os.environ['APPCONFIG_APP_ID'],
        EnvironmentIdentifier=os.environ['APPCONFIG_ENV_ID'],
        ConfigurationProfileIdentifier=os.environ['APPCONFIG_PROFILE_ID'],
    )['InitialConfigurationToken']

    # Fetch the configuration
    response = appconfig.get_latest_configuration(ConfigurationToken=session_token)
    content = response['Configuration'].read()
    config = json.loads(content.decode('utf-8'))

    # Extract the active backend config for this lambda
    backend = config['active_backend']
    # TODO: change the way I receive and interpret the config in my lambda handler
    #       so I don't strictly confine this configuration to my data store backend
    data = {backend: config['configs'][lambda_name][backend]}
    return data
