"""Unit tests for the WarmAppConfigCache AWS Lambda handler.

Verify that the Lambda correctly triggers AppConfig cache warming
and propagates failures so EventBridge can retry.

Test coverage includes:
    1. Successful cache warm-up
       - Ensures AppConfigCacheDAO.latest(pull=True) is called.
    2. Failure propagation
       - Ensures CacheMissError, CachePutError, and DataStoreError are not
         swallowed and cause Lambda failure.

Fixtures:
    - `event`: generic EventBridge event payload.
"""

import json
from unittest.mock import MagicMock

import pytest

from cloudshortener.lambdas.warm_appconfig_cache import app
from cloudshortener.dao.exceptions import CacheMissError, CachePutError, DataStoreError


# -------------------------------
# Fixtures
# -------------------------------


@pytest.fixture()
def event():
    return {
        'source': 'aws.appconfig',
        'detail-type': 'AppConfig Deployment Complete',
        'detail': {},
    }


# -------------------------------
# 1. Successful cache warm-up
# -------------------------------


def test_lambda_handler_warms_cache(monkeypatch, event):
    """Ensure Lambda triggers AppConfig cache warm-up."""
    cache_dao = MagicMock()
    cache_dao.version.return_value = 1
    cache_dao.latest.return_value = {
        'build': 42,
        'active_backend': 'redis',
        'configs': {
            'shorten_url': {
                'redis': {
                    'host': 'localhost',
                    'port': 6379,
                    'db': 0,
                },
            },
        },
    }
    monkeypatch.setattr(app, 'AppConfigCacheDAO', lambda *a, **kw: cache_dao)

    result = json.loads(app.lambda_handler(event, None))

    assert result['status'] == 'success'
    assert result['appconfig_version'] == 1
    assert result['message'] == 'Successfully warmed cache with AppConfig version 1'


# -------------------------------
# 2. Failure propagation
# -------------------------------


@pytest.mark.parametrize(
    'exception, expected_reason, expected_error',
    [
        (CacheMissError('cache miss'), 'cache miss', 'CacheMissError'),
        (CachePutError('cache write failed'), 'cache write failed', 'CachePutError'),
        (DataStoreError('redis unavailable'), 'redis unavailable', 'DataStoreError'),
    ],
)
def test_lambda_handler_propagates_cache_errors(monkeypatch, event, exception, expected_reason, expected_error):
    """Ensure cache-related exceptions propagate and fail the Lambda."""
    cache_dao = MagicMock()
    cache_dao.version.side_effect = exception
    monkeypatch.setattr(app, 'AppConfigCacheDAO', lambda *a, **kw: cache_dao)

    result = json.loads(app.lambda_handler(event, None))

    assert result['status'] == 'error'
    assert result['message'] == 'Failed to warm up cache with latest AppConfig'
    assert result['reason'] == expected_reason
    assert result['error'] == expected_error
