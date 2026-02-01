"""Utility functions for application configuration management.

This module provides a standardized interface for Lambda functions to access
configuration data stored in **AWS AppConfig**. Each environment (`APP_ENV`) has
a dedicated AppConfig *Environment* within the shared AppConfig *Application*
identified by `APP_NAME`. Configuration data is stored as a JSON document under
a configuration profile (typically `backend-config`) and deployed to the
corresponding environment.

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

Each Lambda loads its own section (e.g., `"shorten_url"`) from this AppConfig
document, determined by the current application environment.

Typical usage inside a Lambda handler:
    >>> from cloudshortener.utils.config import load_config
    >>> config = load_config('shorten_url')
    >>> print(config['redis']['host'])
    redis-15501.host.docker.internal

TODO:
    - Add schema validation for required configuration keys.
    - Add caching of AppConfig responses for better cold-start performance.
    - Add @require_environment decorator to @_sam_load_local_appconfig.
"""

import os
import json
import functools
import urllib
import logging
from pathlib import Path
from collections.abc import Callable

import boto3

from cloudshortener.types import LambdaConfiguration
from cloudshortener.constants import ENV
from cloudshortener.utils.helpers import require_environment
from cloudshortener.utils.runtime import running_locally
from cloudshortener.exceptions import BadConfigurationError, ConfigurationError, InfrastructureError, MalformedResponseError
from cloudshortener.constants import ENV


logger = logging.getLogger(__name__)


def app_env() -> str:
    return os.environ.get(ENV.App.APP_ENV, 'local').lower()


def app_name() -> str | None:
    return os.environ.get(ENV.App.APP_NAME)


def project_root() -> Path:
    return Path(os.environ.get(ENV.App.PROJECT_ROOT, os.path.dirname(__file__)))


def app_prefix() -> str | None:
    return None if app_name() is None else f'{app_name()}:{app_env()}'


def _sam_load_local_appconfig(func: Callable) -> Callable:  # pragma: no cover
    """Decorator: load AppConfig from a local AppConfig Agent when running under SAM.

    Behavior:
        - If the application is running locally and `APPCONFIG_AGENT_URL` is set
          to a safe local URL, fetch the app configuration JSON from the local
          AppConfig agent.
        - Else, call the wrapped function (which pulls from AWS AppConfig via boto3).

    TODO: use @require_environment decorator and remove this section
    Environment variables used:
        APPCONFIG_AGENT_URL     : Base URL of the local AppConfig Agent (e.g., http://appconfig-agent:2772).
        APPCONFIG_PROFILE_NAME  : Optional profile name (default: "backend-config").
    """

    # ruff: noqa: E701
    def __validate_appconfig_url(url: str) -> str:
        if not url:
            return ''
        components = urllib.parse.urlparse(url)
        if components.scheme not in {'http', 'https'}:
            raise BadConfigurationError(f'Bad scheme {url}')
        if components.hostname not in {'localhost', '127.0.0.1', 'host.docker.internal', 'appconfig-agent'}:
            raise BadConfigurationError(f'Bad host {url}')
        if components.port not in {2772, None}:
            raise BadConfigurationError(f'Bad port {url}')
        return url

    # ruff: enable

    @functools.wraps(func)
    def wrapper(lambda_name: str) -> LambdaConfiguration:
        agent_url = __validate_appconfig_url(os.getenv(ENV.AppConfig.AGENT_URL))
        if not running_locally() or not agent_url:
            return func(lambda_name)

        profile_name = os.getenv(ENV.AppConfig.PROFILE_NAME, 'backend-config')
        url = f'{agent_url}/applications/{app_name()}/environments/{app_env()}/configurations/{profile_name}'

        logger.debug('Trying to load AppConfig from local agent.', extra={'agentUrl': url, 'lambdaName': lambda_name})
        with urllib.request.urlopen(url, timeout=5) as r:  # noqa: S310
            config = json.load(r)

        backend = config['active_backend']
        data = {backend: config['configs'][lambda_name][backend]}
        logger.debug('Loaded AppConfig from local agent.', extra={'lambdaName': lambda_name, 'build': config['build']})
        return data

    return wrapper


def cache_appconfig(func: Callable) -> Callable:
    """Decorator: transparently cache AppConfig documents via ElastiCache.

    Behavior:
        - On normal path:
            * Fetch latest AppConfig document from cache.
            * Extract the per-lambda config for the requested lambda_name.
            * Return the same structure as the wrapped `load_config()`.
        - On any cache/AppConfig infra error:
            * Fall back to the original `load_config()` implementation.
    """

    @functools.wraps(func)
    def wrapper(lambda_name: str) -> LambdaConfiguration:
        from cloudshortener.dao.cache import AppConfigCacheDAO
        from cloudshortener.dao.exceptions import CacheMissError, CachePutError, DataStoreError

        logger.debug('Trying to load AppConfig from cache.', extra={'lambdaName': lambda_name})

        try:
            # Fetch the latest full AppConfig document (pulling/warming cache on MISS)
            dao = AppConfigCacheDAO(prefix=app_prefix())
            document = dao.latest(pull=True)

        except (CacheMissError, CachePutError, DataStoreError, ConfigurationError, InfrastructureError, MalformedResponseError):
            # On any cache / config-structure / env-related issues, fall back
            # to the original (non-cached) implementation.
            return func(lambda_name)

        else:
            # Reproduce the existing load_config() behavior:
            backend = document['active_backend']
            lambda_config = document['configs'][lambda_name]

            logger.debug('Loaded AppConfig from cache.', extra={'lambdaName': lambda_name, 'build': document['build']})
            return {backend: lambda_config[backend]}

    return wrapper


@_sam_load_local_appconfig
@cache_appconfig
@require_environment(ENV.AppConfig.APP_ID, ENV.AppConfig.ENV_ID, ENV.AppConfig.PROFILE_ID)
def load_config(lambda_name: str) -> LambdaConfiguration:
    """Load configuration for a given Lambda from AWS AppConfig.

    Fetches the AppConfig JSON once and returns the section relevant
    to the requested Lambda function (e.g., 'shorten_url', 'redirect_url').
    """
    logger.debug('Trying to load AppConfig from AWS AppConfig.', extra={'lambdaName': lambda_name})

    appconfig = boto3.client('appconfigdata')

    # Start an AppConfig data session
    session_token = appconfig.start_configuration_session(
        ApplicationIdentifier=os.environ[ENV.AppConfig.APP_ID],
        EnvironmentIdentifier=os.environ[ENV.AppConfig.ENV_ID],
        ConfigurationProfileIdentifier=os.environ[ENV.AppConfig.PROFILE_ID],
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
    logger.debug('Loaded AppConfig from AWS AppConfig.', extra={'lambdaName': lambda_name, 'build': config['build']})
    return data
