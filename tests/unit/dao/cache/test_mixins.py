"""Unit tests for cache mixins (ElastiCacheClientMixin)

Test coverage includes:

1. Initialization and configuration
   - Ensures correct initialization using provided SSM/Secrets clients.
   - Verifies redis client is constructed with resolved host/port/db/auth.
   - Confirms key schema is initialized with the provided prefix.

2. Username resolution precedence
   - Secret username overrides SSM username.
   - Falls back to SSM username when secret omits it.
   - Uses None when both secret username and SSM user param are absent.
"""

import json
from unittest.mock import MagicMock, patch

import pytest
import redis

from cloudshortener.dao.cache.mixins import ElastiCacheClientMixin
from cloudshortener.dao.cache.cache_key_schema import CacheKeySchema
from cloudshortener.utils.constants import (
    ELASTICACHE_HOST_PARAM_ENV,
    ELASTICACHE_PORT_PARAM_ENV,
    ELASTICACHE_DB_PARAM_ENV,
    ELASTICACHE_USER_PARAM_ENV,
    ELASTICACHE_SECRET_ENV,
)

# -------------------------------
# Fixtures
# -------------------------------


@pytest.fixture
def app_prefix():
    """Provide a consistent Redis key prefix for testing."""
    return 'testapp:test'


@pytest.fixture(autouse=True)
def env_vars(monkeypatch):
    """Set required env var names used by the mixin."""
    monkeypatch.setenv(ELASTICACHE_HOST_PARAM_ENV, '/cloudshortener/dev/elasticache/host')
    monkeypatch.setenv(ELASTICACHE_PORT_PARAM_ENV, '/cloudshortener/dev/elasticache/port')
    monkeypatch.setenv(ELASTICACHE_DB_PARAM_ENV, '/cloudshortener/dev/elasticache/db')
    monkeypatch.setenv(ELASTICACHE_USER_PARAM_ENV, '/cloudshortener/dev/elasticache/user')
    monkeypatch.setenv(ELASTICACHE_SECRET_ENV, 'cloudshortener/dev/elasticache/credentials')
    yield


@pytest.fixture
def ssm_client():
    """Mock an SSM client returning host/port/db/user."""
    client = MagicMock(spec=['get_parameter'])

    def _get_parameter(Name):  # noqa: N803
        if Name.endswith('/host'):
            return {'Parameter': {'Value': 'cache.internal'}}
        if Name.endswith('/port'):
            return {'Parameter': {'Value': '6380'}}
        if Name.endswith('/db'):
            return {'Parameter': {'Value': '5'}}
        if Name.endswith('/user'):
            return {'Parameter': {'Value': 'user_from_ssm'}}
        raise KeyError('Unknown parameter')

    client.get_parameter.side_effect = _get_parameter
    return client


@pytest.fixture
def secrets_client():
    """Mock a Secrets Manager client returning username/password."""
    client = MagicMock(spec=['get_secret_value'])
    client.get_secret_value.return_value = {'SecretString': json.dumps({'username': 'user_from_secret', 'password': 'p'})}
    return client


@pytest.fixture
def secrets_client_no_username():
    """Mock a Secrets Manager client returning only password (no username)."""
    client = MagicMock(spec=['get_secret_value'])
    client.get_secret_value.return_value = {'SecretString': json.dumps({'password': 'p'})}
    return client


@pytest.fixture
def redis_client():
    """Provide a reusable redis client mock with a successful ping."""
    r = MagicMock(spec=redis.Redis)
    r.ping.return_value = True
    r.connection_pool = MagicMock()
    r.connection_pool.connection_kwargs = {'host': 'cache.internal', 'port': 6380, 'db': 5}
    return r


# -------------------------------
# 1. Initialization and configuration
# -------------------------------


def test_initialization_constructs_redis_and_keys(app_prefix, ssm_client, secrets_client, redis_client):
    """Ensure mixin constructs redis client with resolved params and initializes key schema."""
    with patch('cloudshortener.dao.cache.mixins.redis.Redis', autospec=True) as redis_mock:
        redis_mock.return_value = redis_client

        dao = ElastiCacheClientMixin(
            prefix=app_prefix,
            ssm_client=ssm_client,
            secrets_client=secrets_client,
            redis_decode_responses=True,
        )

        # Redis client constructed with resolved args (subset assertions)
        _, kwargs = redis_mock.call_args
        assert kwargs['host'] == 'cache.internal'
        assert kwargs['port'] == 6380
        assert kwargs['db'] == 5
        assert kwargs['username'] == 'user_from_secret'  # secret wins
        assert kwargs['password'] == 'p'
        assert kwargs['decode_responses'] is True

        # Healthcheck on init
        redis_client.ping.assert_called_once()

        # Key schema set up with prefix and correct type
        assert isinstance(dao.keys, CacheKeySchema)
        assert dao.keys.prefix == app_prefix

        # Internal redis set correctly
        assert dao.redis is redis_client


# -------------------------------
# 2. Username resolution precedence
# -------------------------------


def test_secret_username_overrides_ssm_username(app_prefix, ssm_client, secrets_client, redis_client):
    """Ensure secret.username takes precedence over SSM-provided username."""
    with patch('cloudshortener.dao.cache.mixins.redis.Redis', autospec=True) as redis_mock:
        redis_mock.return_value = redis_client

        ElastiCacheClientMixin(prefix=app_prefix, ssm_client=ssm_client, secrets_client=secrets_client)

        _, kwargs = redis_mock.call_args
        assert kwargs['username'] == 'user_from_secret'
        assert kwargs['password'] == 'p'


def test_fallback_to_ssm_username_when_secret_omits_username(app_prefix, ssm_client, secrets_client_no_username, redis_client):
    """Ensure mixin falls back to SSM username when secret omits it."""
    with patch('cloudshortener.dao.cache.mixins.redis.Redis', autospec=True) as redis_mock:
        redis_mock.return_value = redis_client

        ElastiCacheClientMixin(prefix=app_prefix, ssm_client=ssm_client, secrets_client=secrets_client_no_username)

        _, kwargs = redis_mock.call_args
        assert kwargs['username'] == 'user_from_ssm'
        assert kwargs['password'] == 'p'


def test_username_none_when_no_secret_username_and_no_ssm_user_param(
    app_prefix, ssm_client, secrets_client_no_username, redis_client, monkeypatch
):
    """Ensure username is None when neither secret nor SSM supplies it."""
    # Remove SSM user param env var; secret also omits username
    monkeypatch.delenv(ELASTICACHE_USER_PARAM_ENV, raising=False)

    with patch('cloudshortener.dao.cache.mixins.redis.Redis', autospec=True) as redis_mock:
        redis_mock.return_value = redis_client

        ElastiCacheClientMixin(prefix=app_prefix, ssm_client=ssm_client, secrets_client=secrets_client_no_username)

        _, kwargs = redis_mock.call_args
        assert kwargs.get('username') is None
        assert kwargs['password'] == 'p'
