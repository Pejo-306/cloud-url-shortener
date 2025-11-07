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

6. Monthly user quota hit
   - Ensure lambda won't create a short URL if the user has hit their quota.

7. Unathorized access attemp
   - Ensure lambda only runs if the event provides Amazon Cognito information about the user.

Fixtures:
    - `apigw_event`: generic API Gateway event structure.
    - `successful_event_200`: valid request body for URL shortening.
    - `bad_request_400`: malformed JSON input.
    - `bad_request_400_no_target_url`: valid JSON missing `target_url`.
    - `context`: mock AWS Lambda context object.
    - `config`: application configuration mock.
    - `base_url`: mocked base URL used in response construction.
    - `short_url_dao`: mock DAO implementing ShortURLBaseDAO.
    - `user_dao`: mock DAO implementing UserBaseDAO.
    - `_patch_lambda_dependencies`: autouse fixture that monkeypatches app dependencies
                                    (config, DAO, shortcode generator, and base URL).
"""

import json
from unittest.mock import MagicMock, patch

import pytest

from cloudshortener.lambdas.shorten_url import app
from cloudshortener.models import ShortURLModel
from cloudshortener.dao.base import ShortURLBaseDAO, UserBaseDAO
from cloudshortener.dao.exceptions import ShortURLAlreadyExistsError


# -------------------------------
# Fixtures
# -------------------------------


@pytest.fixture()
def apigw_event():
    return {
        'body': '{ "test": "body"}',
        'resource': '/{proxy+}',
        'requestContext': {'resourcePath': '/{proxy+}', 'httpMethod': 'POST'},
        'headers': {'User-Agent': 'pytest', 'Authorization': 'Bearer fake-jwt-token'},
        'httpMethod': 'POST',
        'path': '/examplepath',
        'requestContext': {
            'resourcePath': '/{proxy+}',
            'httpMethod': 'POST',
            'domainName': 'testhost:1000',
            'stage': 'test',
            'authorizer': {
                'claims': {'sub': 'user123', 'email': 'pytest@example.com', 'cognito:username': 'pytest-user', 'email_verified': 'true'}
            },
        },
    }


@pytest.fixture()
def successful_event_200():
    return {
        'body': json.dumps({'target_url': 'https://example.com/blog/chuck-norris-is-awesome'}),
        'resource': '/v1/shorten',
        'requestContext': {'resourcePath': '/v1/shorten', 'httpMethod': 'POST'},
        'headers': {'User-Agent': 'pytest', 'Authorization': 'Bearer fake-jwt-token'},
        'httpMethod': 'POST',
        'path': '/v1/shorten',
        'requestContext': {
            'resourcePath': '/v1/shorten',
            'httpMethod': 'POST',
            'domainName': 'testhost:1000',
            'stage': 'test',
            'authorizer': {
                'claims': {'sub': 'user123', 'email': 'pytest@example.com', 'cognito:username': 'pytest-user', 'email_verified': 'true'}
            },
        },
    }


@pytest.fixture()
def bad_request_400():
    return {
        'body': '{"invalid_json": true',
        'resource': '/v1/shorten',
        'headers': {'User-Agent': 'pytest', 'Authorization': 'Bearer fake-jwt-token'},
        'httpMethod': 'POST',
        'path': '/v1/shorten',
        'requestContext': {
            'resourcePath': '/v1/shorten',
            'httpMethod': 'POST',
            'domainName': 'testhost:1000',
            'stage': 'test',
            'authorizer': {
                'claims': {'sub': 'user123', 'email': 'pytest@example.com', 'cognito:username': 'pytest-user', 'email_verified': 'true'}
            },
        },
    }


@pytest.fixture()
def bad_request_400_no_target_url():
    return {
        'body': json.dumps({'invalid_json': True}),
        'resource': '/v1/shorten',
        'headers': {'User-Agent': 'pytest', 'Authorization': 'Bearer fake-jwt-token'},
        'httpMethod': 'POST',
        'path': '/v1/shorten',
        'requestContext': {
            'resourcePath': '/v1/shorten',
            'httpMethod': 'POST',
            'domainName': 'testhost:1000',
            'stage': 'test',
            'authorizer': {
                'claims': {'sub': 'user123', 'email': 'pytest@example.com', 'cognito:username': 'pytest-user', 'email_verified': 'true'}
            },
        },
    }


@pytest.fixture()
def context():
    class _Context:
        function_name = 'shorten_url'

    return _Context()


@pytest.fixture()
def config():
    return {'redis': {'host': 'redis.test', 'port': 6379, 'db': 0}}


@pytest.fixture()
def short_url_dao():
    return MagicMock(spec=ShortURLBaseDAO)


@pytest.fixture()
def user_dao():
    _dao = MagicMock(spec=UserBaseDAO)
    _dao.quota.return_value = 10
    _dao.increment_quota.return_value = 11
    return _dao


@pytest.fixture(autouse=True)
def _patch_lambda_dependencies(monkeypatch, config, short_url_dao, user_dao):
    monkeypatch.setattr(app, 'load_config', lambda *a, **kw: config)
    monkeypatch.setattr(app, 'generate_shortcode', lambda *a, **kw: 'abc123')
    monkeypatch.setattr(app, 'ShortURLRedisDAO', lambda *a, **kw: short_url_dao)
    monkeypatch.setattr(app, 'UserRedisDAO', lambda *a, **kw: user_dao)


# -------------------------------
# 1. Successful shortening
# -------------------------------


def test_lambda_handler(successful_event_200, context, short_url_dao, user_dao):
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

    # Assert ShortURLBaseDAO operations were called correctly
    short_url = ShortURLModel(target=target_url, shortcode='abc123')
    short_url_dao.count.assert_called_once_with(increment=True)
    short_url_dao.insert.assert_called_once_with(short_url=short_url)

    # Assert UserBaseDAO operations were called correctly
    user_dao.quota.assert_called_once_with(user_id='user123')
    user_dao.increment_quota.assert_called_once_with(user_id='user123')


# -------------------------------
# 2. Invalid JSON body
# -------------------------------


def test_lambda_handler_with_invalid_json(bad_request_400, context):
    """Ensure invalid JSON body returns HTTP 400 Bad Request."""
    response = app.lambda_handler(bad_request_400, context)
    body = json.loads(response['body'])

    assert response['statusCode'] == 400
    assert body['message'] == 'Bad Request (invalid JSON body)'


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
        assert body['message'] == 'Internal Server Error'


# -------------------------------
# 5. Short URL already exists
# -------------------------------


def test_lambda_handler_with_existing_short_url(successful_event_200, context, short_url_dao):
    """Ensure lambda wont overwrite an existing short URL and raise HTTP 500."""
    short_url_dao.insert.side_effect = ShortURLAlreadyExistsError()

    response = app.lambda_handler(successful_event_200, context)
    body = json.loads(response['body'])

    assert response['statusCode'] == 500
    assert body['message'] == 'Internal Server Error'


# -------------------------------
# 6. Monthly link generation quota reached
# -------------------------------


def test_lambda_handler_with_quota_reached(monkeypatch, successful_event_200, context, user_dao):
    """Ensure lambda wont create a short URL if the monthly quota is reached."""
    monkeypatch.setattr(app, 'DEFAULT_LINK_GENERATION_QUOTA', 30)
    user_dao.quota.return_value = 30

    response = app.lambda_handler(successful_event_200, context)
    body = json.loads(response['body'])

    assert response['statusCode'] == 429
    assert body['message'] == 'Too many link generation requests: monthly quota reached'


# -------------------------------
# 7. Unathorized access attempt (missing Cognito user id)
# -------------------------------
def test_lambda_handler_with_unauthorized_access_attempt(successful_event_200, context):
    """Ensure lambda wont create a short URL if the Amazon Cognito user id is missing."""
    del successful_event_200['requestContext']['authorizer']
    response = app.lambda_handler(successful_event_200, context)
    body = json.loads(response['body'])

    assert response['statusCode'] == 401
    assert body['message'] == "Unathorized: missing 'sub' in JWT claims"
