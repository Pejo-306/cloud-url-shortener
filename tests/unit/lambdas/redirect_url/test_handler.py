"""Unit tests for the redirect_url AWS Lambda handler.

Verify the handler responds with proper HTTP status codes, validates
path parameters, handles configuration errors, and interacts correctly
with the DAO layer.

Test coverage includes:
    1. Successful redirect
       - Ensures valid shortcodes return a 302 redirect with correct Location header.
    2. Invalid path parameters
       - Ensures requests missing the `shortcode` parameter return HTTP 400.
    3. Invalid shortcode
       - Ensure non-existing shortcodes raise HTTP 400.
    4. Link quota exceeded
       - Ensures requests exceeding monthly quota return HTTP 429.
       - Validates multiple consecutive quota-exceeded requests return HTTP 429.
    5. Configuration errors
       - Ensures missing or unreadable config files result in HTTP 500 responses.

Fixtures:
    - `apigw_event`: generic API Gateway GET event.
    - `successful_event_302`: valid event containing a shortcode.
    - `bad_request_400`: event missing required `shortcode`.
    - `target_url`: mock target URL representing the redirection target.
    - `base_url`: mocked base URL used in response construction.
    - `context`: mock AWS Lambda context object.
    - `config`: mock Redis configuration.
    - `dao`: mock DAO implementing ShortURLBaseDAO with stubbed `get` and `hit` methods.
    - `_patch_lambda_dependencies`: autouse fixture patching app dependencies.
"""

import json
from datetime import datetime, timedelta, UTC
from unittest.mock import MagicMock, patch
import pytest
from freezegun import freeze_time

from cloudshortener.lambdas.redirect_url import app
from cloudshortener.models import ShortURLModel
from cloudshortener.dao.base import ShortURLBaseDAO
from cloudshortener.dao.exceptions import ShortURLNotFoundError


# -------------------------------
# Fixtures
# -------------------------------


@pytest.fixture()
def apigw_event():
    return {
        'resource': '/{shortcode}',
        'requestContext': {'resourcePath': '/{shortcode}', 'httpMethod': 'GET'},
        'pathParameters': {'apigw': 'event'},
        'httpMethod': 'GET',
        'path': '/abc123',
        'requestContext': {'domainName': 'testhost:1000', 'stage': 'test'},
    }


@pytest.fixture()
def successful_event_302():
    return {
        'resource': '/{shortcode}',
        'requestContext': {'resourcePath': '/{shortcode}', 'httpMethod': 'GET'},
        'pathParameters': {'shortcode': 'abc123'},
        'httpMethod': 'GET',
        'path': '/abc123',
        'requestContext': {'domainName': 'testhost:1000', 'stage': 'test'},
    }


@pytest.fixture()
def bad_request_400():
    return {
        'resource': '/{shortcode}',
        'requestContext': {'resourcePath': '/{shortcode}', 'httpMethod': 'GET'},
        'pathParameters': {'invalid': 'path'},
        'httpMethod': 'GET',
        'path': '/abc123',
        'requestContext': {'domainName': 'testhost:1000', 'stage': 'test'},
    }


@pytest.fixture()
def target_url():
    return 'https://example.com/blog/chuck-norris-is-awesome'


@pytest.fixture()
def base_url():
    return 'https://testhost:1000'


@pytest.fixture()
def context():
    class _Context:
        function_name = 'redirect_url'

    return _Context()


@pytest.fixture()
def config():
    return {'redis': {'host': 'redis.test', 'port': 6379, 'db': 0}}


@pytest.fixture()
def dao(target_url):
    _dao = MagicMock(spec=ShortURLBaseDAO)
    _dao.get.return_value = ShortURLModel(
        target=target_url,
        shortcode='abc123',
        hits=10000,
        expires_at=datetime.now(UTC) + timedelta(days=10),
    )
    _dao.hit.return_value = 9999  # Default: quota not exceeded
    return _dao


@pytest.fixture(autouse=True)
def _patch_lambda_dependencies(monkeypatch, config, dao):
    """Automatically patch Lambda dependencies for all tests."""
    monkeypatch.setattr(app, 'load_config', lambda *a, **kw: config)
    monkeypatch.setattr(app, 'ShortURLRedisDAO', lambda *a, **kw: dao)


# -------------------------------
# 1. Successful redirect
# -------------------------------


def test_lambda_handler(successful_event_302, context, dao, target_url):
    """Ensure Lambda correctly redirects valid shortcodes (HTTP 302)."""
    response = app.lambda_handler(successful_event_302, context)
    headers = response['headers']
    body = json.loads(response['body'])

    # Assert successful redirect response
    assert response['statusCode'] == 302
    assert body == {}
    assert headers['Location'] == target_url

    # Assert DAO methods were called correctly
    dao.hit.assert_called_once_with(shortcode='abc123')
    dao.get.assert_called_once_with(shortcode='abc123')


# -------------------------------
# 2. Invalid path parameters
# -------------------------------


def test_lambda_handler_with_invalid_path_parameters(bad_request_400, context):
    """Ensure missing `shortcode` path parameter returns HTTP 400."""
    response = app.lambda_handler(bad_request_400, context)
    body = json.loads(response['body'])

    assert response['statusCode'] == 400
    assert body['message'] == "Bad Request (missing 'shortcode' in path)"


# -------------------------------
# 3. Invalid shortcode
# -------------------------------


def test_lambda_handler_with_invalid_shortcode(successful_event_302, context, dao, base_url):
    """Ensure non-existing shortcodes raise HTTP 400."""
    # Ensure the DAO raises ShortURLNotFoundError on hit()
    dao.hit.side_effect = ShortURLNotFoundError()
    short_url = f'{base_url}/abc123'

    response = app.lambda_handler(successful_event_302, context)
    body = json.loads(response['body'])

    assert response['statusCode'] == 400
    assert body['message'] == f"Bad Request (short url {short_url} doesn't exist)"
    dao.hit.assert_called_once_with(shortcode='abc123')
    dao.get.assert_not_called()


# -------------------------------
# 4. Link quota exceeded
# -------------------------------


@freeze_time('2025-10-15')
def test_lambda_handler_with_quota_exceeded(successful_event_302, context, dao):
    """Ensure requests exceeding monthly quota return HTTP 429."""
    dao.hit.return_value = -1  # Quota exceeded

    response = app.lambda_handler(successful_event_302, context)
    body = json.loads(response['body'])
    headers = response['headers']

    assert response['statusCode'] == 429
    assert headers['Content-Type'] == 'application/json'
    assert 'Retry-After' in headers
    assert body['errorCode'] == 'LINK_QUOTA_EXCEEDED'
    assert 'Monthly hit quota exceeded for link' in body['message']
    assert '2025-11-01T00:00:00Z' in body['message']
    dao.hit.assert_called_once_with(shortcode='abc123')
    dao.get.assert_not_called()


@freeze_time('2025-10-15')
def test_lambda_handler_with_multiple_quota_exceeded_requests(successful_event_302, context, dao):
    """Ensure multiple consecutive quota-exceeded requests return HTTP 429."""
    dao.hit.return_value = -5  # Quota exceeded by 5

    # First request
    response1 = app.lambda_handler(successful_event_302, context)
    body1 = json.loads(response1['body'])

    assert response1['statusCode'] == 429
    assert body1['errorCode'] == 'LINK_QUOTA_EXCEEDED'

    # Second request (quota still exceeded)
    response2 = app.lambda_handler(successful_event_302, context)
    body2 = json.loads(response2['body'])

    assert response2['statusCode'] == 429
    assert body2['errorCode'] == 'LINK_QUOTA_EXCEEDED'

    # Third request (quota still exceeded)
    response3 = app.lambda_handler(successful_event_302, context)
    body3 = json.loads(response3['body'])

    assert response3['statusCode'] == 429
    assert body3['errorCode'] == 'LINK_QUOTA_EXCEEDED'

    # Verify hit() was called for each request
    assert dao.hit.call_count == 3
    dao.get.assert_not_called()


# -------------------------------
# 5. Configuration errors
# -------------------------------


def test_lambda_handler_with_invalid_configuration_file(apigw_event, context):
    """Ensure missing or unreadable config file raises HTTP 500."""
    with patch('cloudshortener.lambdas.redirect_url.app.load_config') as mock_load_config:
        mock_load_config.side_effect = FileNotFoundError('Something goes wrong')
        response = app.lambda_handler(apigw_event, context)
        body = json.loads(response['body'])

        assert response['statusCode'] == 500
        assert body['message'] == 'Internal Server Error'
