"""Unit tests for the AppConfigCacheDAO

This test suite verifies the Redis-backed caching behavior for AWS AppConfig
documents, including cache HIT/MISS flows, optional fetch-and-warm on MISS,
and error handling.

Test coverage includes:

1. Latest document retrieval
   - Returns cached latest document on HIT
   - Raises CacheMissError on MISS with pull=False
   - Fetches from AppConfig and warms cache on MISS with pull=True

2. Versioned document retrieval
   - Returns cached versioned document on HIT
   - Raises CacheMissError on MISS with pull=False
   - Fetches specific version and warms cache on MISS with pull=True

3. Versioned metadata retrieval
   - Returns cached metadata on HIT
   - Raises CacheMissError on MISS with pull=False
   - Fetches specific version metadata and warms cache on MISS with pull=True

4. Cache write failures
   - Raises CachePutError if Redis write fails during warm-up

5. Environment validation
   - Raises ValueError when required AppConfig env vars are missing for fetches
"""

import json
from io import BytesIO
from unittest.mock import MagicMock, call

import pytest
import redis
from freezegun import freeze_time

from cloudshortener.dao.cache.cache_key_schema import CacheKeySchema
from cloudshortener.dao.cache.appconfig_cache_dao import AppConfigCacheDAO
from cloudshortener.dao.exceptions import CacheMissError, CachePutError


# -------------------------------
# Autouse environment
# -------------------------------


@pytest.fixture(autouse=True)
def _env(monkeypatch):
    """Set up environment variables for testing."""
    # AppConfig env vars
    monkeypatch.setenv('APPCONFIG_APP_ID', 'app123')
    monkeypatch.setenv('APPCONFIG_ENV_ID', 'env123')
    monkeypatch.setenv('APPCONFIG_PROFILE_ID', 'prof123')

    # ElastiCache env vars (not used directly in these tests, but kept consistent)
    monkeypatch.setenv('ELASTICACHE_HOST_PARAM', '/test/elasticache/host')
    monkeypatch.setenv('ELASTICACHE_PORT_PARAM', '/test/elasticache/port')
    monkeypatch.setenv('ELASTICACHE_DB_PARAM', '/test/elasticache/db')
    monkeypatch.setenv('ELASTICACHE_USER_PARAM', '/test/elasticache/user')
    monkeypatch.setenv('ELASTICACHE_SECRET', 'test/elasticache/creds')


# -------------------------------
# Default AppConfig document and metadata
# -------------------------------

@pytest.fixture
def default_appconfig_doc():
    return {
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
        }
    }


@pytest.fixture
def default_appconfig_metadata():
    return {
        'version': 42,
        'etag': 'W/"etag-latest"',
        'content_type': 'application/json',
        'fetched_at': '2025-01-03T00:00:00+00:00',
    }


# -------------------------------
# Global boto3 client mocks
# -------------------------------


@pytest.fixture
def appconfigdata_client(default_appconfig_doc, default_appconfig_metadata):
    """Mock AppConfigData client used for fetching 'latest'."""
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
        }
    }
    return client


@pytest.fixture
def appconfig_client(default_appconfig_doc, default_appconfig_metadata):
    """Mock AppConfig control-plane client used for fetching specific versions."""
    client = MagicMock()
    client.get_hosted_configuration_version.return_value = {
        'Content': BytesIO(json.dumps(default_appconfig_doc).encode('utf-8')),
        'ContentType': 'application/json',
        'ResponseMetadata': {
            'HTTPHeaders': {
                'configuration-version': str(default_appconfig_metadata['version']),
                'etag': default_appconfig_metadata['etag'],
            },
        }
    }
    return client


@pytest.fixture(autouse=True)
def _boto3_client(monkeypatch, appconfigdata_client, appconfig_client):
    """Monkeypatch boto3.client globally for this test module."""
    import boto3 as _boto3

    def _client(service_name: str, *args, **kwargs):
        if service_name == 'appconfigdata':
            return appconfigdata_client
        if service_name == 'appconfig':
            return appconfig_client
        raise AssertionError(f'Unexpected boto3 client requested: {service_name}')

    monkeypatch.setattr(_boto3, 'client', _client)


# -------------------------------
# Fixtures
# -------------------------------


@pytest.fixture
def app_prefix():
    """Provide a consistent Redis key prefix for testing."""
    return 'testapp:test'


@pytest.fixture
def redis_client():
    """Mock a Redis client with pipeline support."""
    client = MagicMock(spec=redis.Redis)

    pipe = MagicMock()
    pipe.__enter__.return_value = pipe
    pipe.__exit__.return_value = None
    # By default, pipeline.execute() succeeds
    pipe.execute.return_value = None

    client.pipeline.return_value = pipe
    client.get.return_value = None  # default: cache MISS

    # Expose pipe for assertions where needed
    client._pipe = pipe
    return client


@pytest.fixture
def dao(redis_client, app_prefix):
    """Instantiate AppConfigCacheDAO with injected redis client and key schema."""
    _dao = object.__new__(AppConfigCacheDAO)  # bypass mixin/network init
    _dao.redis = redis_client
    _dao.keys = CacheKeySchema(prefix=app_prefix)
    return _dao


# -------------------------------
# 1. Latest document retrieval
# -------------------------------


def test_latest_cache_hit_returns_document(dao, redis_client, default_appconfig_doc):
    """Ensure latest() returns cached document on HIT."""
    redis_client.get.return_value = json.dumps(default_appconfig_doc)

    result = dao.latest(pull=False)

    assert isinstance(result, dict)
    assert result['active_backend'] == 'redis'
    assert result['configs']['shorten_url']['redis']['host'] == 'localtest'
    assert result['configs']['shorten_url']['redis']['port'] == 96379
    assert result['configs']['shorten_url']['redis']['db'] == 42
    assert result['configs']['redirect_url']['redis']['host'] == 'localtest'
    assert result['configs']['redirect_url']['redis']['port'] == 66379
    assert result['configs']['redirect_url']['redis']['db'] == 24

    redis_client.get.assert_called_once_with('testapp:test:appconfig:latest')


def test_latest_cache_miss_with_pull_false_raises(dao, redis_client):
    """Ensure latest() raises CacheMissError on MISS when pull=False."""
    redis_client.get.return_value = None
    with pytest.raises(CacheMissError, match='latest'):
        dao.latest(pull=False)


@freeze_time('2025-01-03T00:00:00Z')
def test_latest_cache_miss_with_pull_true_fetches_and_writes(dao, redis_client, default_appconfig_doc, default_appconfig_metadata):
    """Ensure latest() fetches from AppConfig and warms cache on MISS with pull=True."""
    expected_calls = [
        call('testapp:test:appconfig:v42', json.dumps(default_appconfig_doc, separators=(',', ':'), ensure_ascii=False)),
        call('testapp:test:appconfig:v42:metadata', json.dumps(default_appconfig_metadata, separators=(',', ':'), ensure_ascii=False)),
        call('testapp:test:appconfig:latest', json.dumps(default_appconfig_doc, separators=(',', ':'), ensure_ascii=False)),
    ]
    redis_client.get.return_value = None

    result = dao.latest(pull=True)

    # Verify returned document
    assert isinstance(result, dict)
    assert result['active_backend'] == 'redis'
    assert result['configs']['shorten_url']['redis']['host'] == 'localtest'
    assert result['configs']['shorten_url']['redis']['port'] == 96379
    assert result['configs']['shorten_url']['redis']['db'] == 42
    assert result['configs']['redirect_url']['redis']['host'] == 'localtest'
    assert result['configs']['redirect_url']['redis']['port'] == 66379
    assert result['configs']['redirect_url']['redis']['db'] == 24

    # Verify warm-up writes: v{n}, v{n}:metadata, and latest
    pipe = redis_client._pipe
    assert pipe.set.call_count == 3
    pipe.set.assert_has_calls(expected_calls)
    pipe.execute.assert_called_once()


# -------------------------------
# 2. Versioned document retrieval
# -------------------------------


def test_get_version_cache_hit_returns_document(dao, redis_client, default_appconfig_doc):
    """Ensure get(version) returns cached document on HIT."""
    redis_client.get.return_value = json.dumps(default_appconfig_doc)

    result = dao.get(42, pull=False)

    assert isinstance(result, dict)
    assert result['active_backend'] == 'redis'
    assert result['configs']['shorten_url']['redis']['host'] == 'localtest'
    assert result['configs']['shorten_url']['redis']['port'] == 96379
    assert result['configs']['shorten_url']['redis']['db'] == 42
    assert result['configs']['redirect_url']['redis']['host'] == 'localtest'
    assert result['configs']['redirect_url']['redis']['port'] == 66379
    assert result['configs']['redirect_url']['redis']['db'] == 24

    redis_client.get.assert_called_once_with('testapp:test:appconfig:v42')


def test_get_version_cache_miss_with_pull_false_raises(dao, redis_client):
    """Ensure get(version) raises CacheMissError on MISS when pull=False."""
    redis_client.get.return_value = None
    with pytest.raises(CacheMissError, match='v42'):
        dao.get(42, pull=False)


@freeze_time('2025-01-03T00:00:00Z')
def test_get_version_cache_miss_with_pull_true_fetches_and_writes(dao, redis_client, default_appconfig_doc, default_appconfig_metadata):
    """Ensure get(version) fetches specific version and warms cache on MISS with pull=True."""
    written_appconfig_metadata = default_appconfig_metadata.copy()
    written_appconfig_metadata['version'] = 9
    expected_calls = [
        call('testapp:test:appconfig:v9', json.dumps(default_appconfig_doc, separators=(',', ':'), ensure_ascii=False)),
        call('testapp:test:appconfig:v9:metadata', json.dumps(written_appconfig_metadata, separators=(',', ':'), ensure_ascii=False)),
    ]
    redis_client.get.return_value = None

    result = dao.get(9, pull=True)

    # Verify returned document
    assert isinstance(result, dict)
    assert result['active_backend'] == 'redis'
    assert result['configs']['shorten_url']['redis']['host'] == 'localtest'
    assert result['configs']['shorten_url']['redis']['port'] == 96379
    assert result['configs']['shorten_url']['redis']['db'] == 42
    assert result['configs']['redirect_url']['redis']['host'] == 'localtest'
    assert result['configs']['redirect_url']['redis']['port'] == 66379
    assert result['configs']['redirect_url']['redis']['db'] == 24

    # Verify warm-up writes: v{n}, v{n}:metadata, and latest
    pipe = redis_client._pipe
    assert pipe.set.call_count == 2
    pipe.set.assert_has_calls(expected_calls)
    pipe.execute.assert_called_once()


# -------------------------------
# 3. Versioned metadata retrieval
# -------------------------------


def test_metadata_cache_hit_returns_metadata(dao, redis_client, default_appconfig_metadata):
    """Ensure metadata(version) returns cached metadata on HIT."""
    redis_client.get.return_value = json.dumps(default_appconfig_metadata)

    result = dao.metadata(42, pull=False)

    assert isinstance(result, dict)
    assert result['version'] == 42
    assert result['etag'] == 'W/"etag-latest"'
    assert result['content_type'] == 'application/json'
    assert result['fetched_at'] == '2025-01-03T00:00:00+00:00'

    redis_client.get.assert_called_once_with('testapp:test:appconfig:v42:metadata')


def test_metadata_cache_miss_with_pull_false_raises(dao, redis_client):
    """Ensure metadata(version) raises CacheMissError on MISS when pull=False."""
    redis_client.get.return_value = None
    with pytest.raises(CacheMissError, match='metadata'):
        dao.metadata(11, pull=False)


@freeze_time('2025-01-03T00:00:00Z')
def test_metadata_cache_miss_with_pull_true_fetches_and_writes(dao, redis_client, default_appconfig_doc, default_appconfig_metadata):
    """Ensure metadata(version) fetches and warms cache on MISS with pull=True."""
    written_appconfig_metadata = default_appconfig_metadata.copy()
    written_appconfig_metadata['version'] = 9
    expected_calls = [
        call('testapp:test:appconfig:v9', json.dumps(default_appconfig_doc, separators=(',', ':'), ensure_ascii=False)),
        call('testapp:test:appconfig:v9:metadata', json.dumps(written_appconfig_metadata, separators=(',', ':'), ensure_ascii=False)),
    ]
    redis_client.get.return_value = None

    result = dao.metadata(9, pull=True)

    # Verify returned document
    assert isinstance(result, dict)
    assert result['version'] == 9
    assert result['etag'] == 'W/"etag-latest"'
    assert result['content_type'] == 'application/json'
    assert result['fetched_at'] == '2025-01-03T00:00:00+00:00'

    # Verify warm-up writes: v{n}, v{n}:metadata, and latest
    pipe = redis_client._pipe
    assert pipe.set.call_count == 2
    pipe.set.assert_has_calls(expected_calls)
    pipe.execute.assert_called_once()


# -------------------------------
# 4. Cache write failures
# -------------------------------


def test_cache_put_error_when_pipeline_execute_fails(dao, redis_client, appconfig_client):
    """Ensure CachePutError is raised when Redis write fails during warm-up."""
    # Cause the pipeline execute to fail
    redis_client.get.return_value = None
    redis_client._pipe.execute.side_effect = redis.exceptions.ConnectionError('Connection error')

    with pytest.raises(CachePutError, match='Failed to write AppConfig v42'):
        dao.get(42, pull=True)


# -------------------------------
# 5. Environment validation
# -------------------------------


def test_fetch_latest_env_validation_missing_vars(dao, monkeypatch):
    """Ensure _fetch_latest_appconfig() validates required env vars."""
    monkeypatch.delenv('APPCONFIG_ENV_ID', raising=False)
    expected_message = "Missing required environment variables: 'APPCONFIG_ENV_ID'"
    with pytest.raises(KeyError, match=expected_message):
        dao.latest(pull=True)


def test_fetch_version_env_validation_missing_vars(dao, monkeypatch):
    """Ensure _fetch_appconfig() validates required env vars."""
    monkeypatch.delenv('APPCONFIG_PROFILE_ID', raising=False)
    expected_message = "Missing required environment variables: 'APPCONFIG_PROFILE_ID'"
    with pytest.raises(KeyError, match=expected_message):
        dao.get(42, pull=True)
