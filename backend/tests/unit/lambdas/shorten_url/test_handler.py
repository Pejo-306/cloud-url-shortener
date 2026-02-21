import json
from typing import cast
from unittest.mock import MagicMock

import pytest
from pytest import MonkeyPatch

from cloudshortener.types import LambdaEvent, LambdaContext, LambdaConfiguration, HttpHeaders
from cloudshortener.constants import DefaultQuota
from cloudshortener.lambdas.shorten_url import app
from cloudshortener.models import ShortURLModel
from cloudshortener.dao.base import ShortURLBaseDAO, UserBaseDAO
from cloudshortener.dao.exceptions import ShortURLAlreadyExistsError


@pytest.fixture
def apigw_event() -> LambdaEvent:
    return cast(
        LambdaEvent,
        {
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
        },
    )


@pytest.fixture
def successful_event_200() -> LambdaEvent:
    return cast(
        LambdaEvent,
        {
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
        },
    )


@pytest.fixture
def bad_request_400() -> LambdaEvent:
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


@pytest.fixture
def bad_request_400_no_target_url() -> LambdaEvent:
    return cast(
        LambdaEvent,
        {
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
        },
    )


class TestShortenUrlHandler:
    @pytest.fixture
    def context(self) -> LambdaContext:
        return cast(LambdaContext, {'function_name': 'shorten_url'})

    @pytest.fixture
    def config(self) -> LambdaConfiguration:
        return cast(LambdaConfiguration, {'redis': {'host': 'redis.test', 'port': 6379, 'db': 0}})

    @pytest.fixture
    def short_url_dao(self) -> ShortURLBaseDAO:
        return cast(ShortURLBaseDAO, MagicMock(spec=ShortURLBaseDAO))

    @pytest.fixture
    def user_dao(self) -> UserBaseDAO:
        dao = cast(UserBaseDAO, MagicMock(spec=UserBaseDAO))
        dao.quota.return_value = 10
        dao.increment_quota.return_value = 11
        return dao

    @pytest.fixture(autouse=True)
    def setup(
        self,
        monkeypatch: MonkeyPatch,
        context: LambdaContext,
        config: LambdaConfiguration,
        short_url_dao: ShortURLBaseDAO,
        user_dao: UserBaseDAO,
    ) -> None:
        # Patch Lambda dependencies
        monkeypatch.setattr(app, 'load_config', lambda *a, **kw: self.config)
        monkeypatch.setattr(app, 'generate_shortcode', lambda *a, **kw: 'abc123')
        monkeypatch.setattr(app, 'ShortURLRedisDAO', lambda *a, **kw: self.short_url_dao)
        monkeypatch.setattr(app, 'UserRedisDAO', lambda *a, **kw: self.user_dao)

        self.context = context
        self.config = config
        self.short_url_dao = short_url_dao
        self.user_dao = user_dao

    def assert_has_cors_headers(self, headers: HttpHeaders) -> None:
        assert headers['Access-Control-Allow-Origin'] == '*'  # TODO: this should be a specific frontend domain only
        assert headers['Access-Control-Allow-Headers'] == 'Authorization,Content-Type'
        assert headers['Access-Control-Allow-Methods'] == 'OPTIONS,POST,GET'

    def test_lambda_handler(self, successful_event_200: LambdaEvent) -> None:
        target_url = 'https://example.com/blog/chuck-norris-is-awesome'

        response = app.lambda_handler(successful_event_200, self.context)
        body = json.loads(response['body'])
        headers = response['headers']

        # Assert Lambda successfully executes
        assert response['statusCode'] == 200
        assert body['message'] == f'Successfully shortened {target_url} to https://testhost:1000/abc123'
        assert body['targetUrl'] == target_url
        assert body['shortUrl'] == 'https://testhost:1000/abc123'
        assert body['shortcode'] == 'abc123'
        assert body['userQuota'] == 11
        assert body['remainingQuota'] == 9
        self.assert_has_cors_headers(headers)

        # Assert Lambda persisted a new short URL
        short_url = ShortURLModel(target=target_url, shortcode='abc123')
        self.short_url_dao.count.assert_called_once_with(increment=True)
        self.short_url_dao.insert.assert_called_once_with(short_url=short_url)

        # Assert user's monthly quota was incremented
        self.user_dao.quota.assert_called_once_with(user_id='user123')
        self.user_dao.increment_quota.assert_called_once_with(user_id='user123')

    def test_lambda_handler_with_invalid_json(self, bad_request_400: LambdaEvent) -> None:
        response = app.lambda_handler(bad_request_400, self.context)
        body = json.loads(response['body'])
        headers = response['headers']

        assert response['statusCode'] == 400
        assert body['message'] == 'Bad Request (invalid JSON body)'
        assert body['errorCode'] == 'INVALID_JSON'
        self.assert_has_cors_headers(headers)

    def test_lambda_handler_with_missing_target_url(self, bad_request_400_no_target_url: LambdaEvent) -> None:
        response = app.lambda_handler(bad_request_400_no_target_url, self.context)
        body = json.loads(response['body'])
        headers = response['headers']

        assert response['statusCode'] == 400
        assert body['message'] == "Bad Request (missing 'target_url' or 'targetUrl' in JSON body)"
        assert body['errorCode'] == 'MISSING_TARGET_URL'
        self.assert_has_cors_headers(headers)

    def test_lambda_handler_with_invalid_configuration_file(
        self,
        monkeypatch: MonkeyPatch,
        apigw_event: LambdaEvent,
    ) -> None:
        mock_load_config = MagicMock(side_effect=FileNotFoundError('Something goes wrong'))
        monkeypatch.setattr(app, 'load_config', mock_load_config)

        response = app.lambda_handler(apigw_event, self.context)
        body = json.loads(response['body'])
        headers = response['headers']

        assert response['statusCode'] == 500
        assert body['message'] == 'Internal Server Error'
        self.assert_has_cors_headers(headers)

    def test_lambda_handler_with_existing_short_url(self, successful_event_200: LambdaEvent) -> None:
        # Assert Short URL DAO won't override an existing short URL
        self.short_url_dao.insert.side_effect = ShortURLAlreadyExistsError()

        response = app.lambda_handler(successful_event_200, self.context)
        body = json.loads(response['body'])
        headers = response['headers']

        assert response['statusCode'] == 409
        assert body['message'] == 'Conflict (short URL already exists)'
        assert body['errorCode'] == 'SHORT_URL_ALREADY_EXISTS'
        self.assert_has_cors_headers(headers)

    def test_lambda_handler_with_quota_reached(self, monkeypatch: MonkeyPatch, successful_event_200: LambdaEvent) -> None:
        class BiggerQuota:
            LINK_HITS = DefaultQuota.LINK_HITS
            LINK_GENERATION = 30

        monkeypatch.setattr(app, 'DefaultQuota', BiggerQuota)
        self.user_dao.quota.return_value = 30

        response = app.lambda_handler(successful_event_200, self.context)
        body = json.loads(response['body'])
        headers = response['headers']

        assert response['statusCode'] == 429
        assert body['message'] == 'Too Many Link Generation Requests (monthly quota reached)'
        assert body['errorCode'] == 'LINK_QUOTA_EXCEEDED'
        self.assert_has_cors_headers(headers)

    def test_lambda_handler_with_unauthorized_access_attempt(self, successful_event_200: LambdaEvent) -> None:
        del successful_event_200['requestContext']['authorizer']

        response = app.lambda_handler(successful_event_200, self.context)
        body = json.loads(response['body'])
        headers = response['headers']

        assert response['statusCode'] == 401
        assert body['message'] == "Unauthorized (missing 'sub' in JWT claims)"
        assert body['errorCode'] == 'MISSING_USER_ID'
        self.assert_has_cors_headers(headers)
