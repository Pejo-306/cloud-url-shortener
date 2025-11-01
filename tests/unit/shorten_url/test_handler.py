"""Unit tests for the shorten_url AWS Lambda handler.

Verify that the Lambda correctly handles incoming API Gateway events,
interacts with the DAO layer, and returns proper HTTP responses in both
success and error scenarios.

Test coverage includes:

1. Successful shortening
   - Ensures the Lambda generates and returns valid short URLs (HTTP 200).

2. Invalid JSON body
   - Ensures malformed request bodies return HTTP 400 with descriptive messages.

3. Missing `target_url` key
   - Ensures requests missing the required field return HTTP 400.

4. Configuration errors
   - Ensures missing or unreadable config files raise HTTP 500 responses.

5. Short URL already exists
   - Ensure lambda wont overwrite an existing short URL and raise HTTP 500.

Fixtures:
    - `apigw_event`: generic API Gateway event structure.
    - `successful_event_200`: valid request body for URL shortening.
    - `bad_request_400`: malformed JSON input.
    - `bad_request_400_no_target_url`: valid JSON missing `target_url`.
    - `context`: mock AWS Lambda context object.
    - `config`: application configuration mock.
    - `base_url`: mocked base URL used in response construction.
    - `dao`: mock DAO implementing ShortURLBaseDAO.
    - `_patch_lambda_dependencies`: autouse fixture that monkeypatches app dependencies
                                    (config, DAO, shortcode generator, and base URL).
"""

import json
from unittest.mock import MagicMock, patch

import pytest

from cloudshortener.lambdas.shorten_url import app
from cloudshortener.models import ShortURLModel
from cloudshortener.dao.base import ShortURLBaseDAO
from cloudshortener.dao.exceptions import ShortURLAlreadyExistsError


# -------------------------------
# Fixtures
# -------------------------------

@pytest.fixture()
def apigw_event():
    return {
        "body": '{ "test": "body"}',
        "resource": "/{proxy+}",
        "requestContext": {"resourcePath": "/{proxy+}", "httpMethod": "POST"},
        "headers": {"User-Agent": "pytest"},
        "httpMethod": "POST",
        "path": "/examplepath",
        "requestContext": {"domainName": "testhost:1000", "stage": "test"}
    }


@pytest.fixture()
def successful_event_200():
    return {
        "body": json.dumps({'target_url': 'https://example.com/blog/chuck-norris-is-awesome'}),
        "resource": "/v1/shorten",
        "requestContext": {"resourcePath": "/v1/shorten", "httpMethod": "POST"},
        "headers": {"Content-Type": "application/json"},
        "httpMethod": "POST",
        "path": "/v1/shorten",
        "requestContext": {"domainName": "testhost:1000", "stage": "test"}
    }


@pytest.fixture()
def bad_request_400():
    return {
        "body": '{"invalid_json": true',
        "resource": "/v1/shorten",
        "headers": {"Content-Type": "application/json"},
        "httpMethod": "POST",
        "path": "/v1/shorten",
        "requestContext": {"domainName": "testhost:1000", "stage": "test"}
    }


@pytest.fixture()
def bad_request_400_no_target_url():
    return {
        "body": json.dumps({'invalid_json': True}),
        "resource": "/v1/shorten",
        "headers": {"Content-Type": "application/json"},
        "httpMethod": "POST",
        "path": "/v1/shorten",
        "requestContext": {"domainName": "testhost:1000", "stage": "test"}
    }


@pytest.fixture()
def context():
    class _Context:
        function_name = 'shorten_url'
    return _Context()


@pytest.fixture()
def config():
    return {
        'redis': {
            'host': 'redis.test',
            'port': 6379,
            'db': 0
        }
    }


@pytest.fixture()
def base_url():
    return 'https://testhost:1000'


@pytest.fixture()
def dao():
    return MagicMock(spec=ShortURLBaseDAO)


@pytest.fixture(autouse=True)
def _patch_lambda_dependencies(monkeypatch, config, base_url, dao):
    monkeypatch.setattr(app, 'load_config', lambda *a, **kw: config)
    monkeypatch.setattr(app, 'base_url', lambda *a, **kw: base_url)
    monkeypatch.setattr(app, 'generate_shortcode', lambda *a, **kw: 'abc123')
    monkeypatch.setattr(app, 'ShortURLRedisDAO', lambda *a, **kw: dao)


# -------------------------------
# 1. Successful shortening
# -------------------------------

def test_lambda_handler(successful_event_200, context, dao):
    """Ensure Lambda successfully shortens URLs and updates datastore."""
    target_url = 'https://example.com/blog/chuck-norris-is-awesome'

    response = app.lambda_handler(successful_event_200, context)
    body = json.loads(response['body'])

    # Assert successful response payload
    assert response['statusCode'] == 200
    assert body['message'] == f'Successfully shortened {target_url} to https://testhost:1000/abc123'
    assert body['target_url'] == target_url
    assert body['short_url'] == 'https://testhost:1000/abc123'
    assert body['shortcode'] == 'abc123'

    # Assert DAO operations were called correctly
    short_url = ShortURLModel(target=target_url, shortcode='abc123')
    dao.count.assert_called_once_with(increment=True)
    dao.insert.assert_called_once_with(short_url=short_url)


# -------------------------------
# 2. Invalid JSON body
# -------------------------------

def test_lambda_handler_with_invalid_json(bad_request_400, context):
    """Ensure invalid JSON body returns HTTP 400 Bad Request."""
    response = app.lambda_handler(bad_request_400, context)
    body = json.loads(response['body'])

    assert response['statusCode'] == 400
    assert body['message'] == "Bad Request (invalid JSON body)"


# -------------------------------
# 3. Missing target_url field
# -------------------------------

def test_lambda_handler_with_missing_target_url(bad_request_400_no_target_url, context):
    """Ensure missing 'target_url' in JSON body returns HTTP 400."""
    response = app.lambda_handler(bad_request_400_no_target_url, context)
    body = json.loads(response['body'])

    assert response['statusCode'] == 400
    assert body['message'] == "Bad Request (missing 'target_url' in JSON body)"


# -------------------------------
# 4. Configuration error handling
# -------------------------------

def test_lambda_handler_with_invalid_configuration_file(apigw_event, context):
    """Ensure FileNotFoundError in load_config raises HTTP 500."""
    with patch('cloudshortener.lambdas.shorten_url.app.load_config') as mock_load_config:
        mock_load_config.side_effect = FileNotFoundError('Something goes wrong')
        response = app.lambda_handler(apigw_event, context)
        body = json.loads(response['body'])

        assert response['statusCode'] == 500
        assert body['message'] == "Internal Server Error"


# -------------------------------
# 5. Short URL already exists
# -------------------------------

def test_lambda_handler_with_existing_short_url(successful_event_200, context, dao):
    """Ensure lambda wont overwrite an existing short URL and raise HTTP 500."""
    dao.insert.side_effect = ShortURLAlreadyExistsError()

    response = app.lambda_handler(successful_event_200, context)
    body = json.loads(response['body'])

    assert response['statusCode'] == 500
    assert body['message'] == "Internal Server Error"

