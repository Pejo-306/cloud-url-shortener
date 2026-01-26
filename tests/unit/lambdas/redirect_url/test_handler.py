import json
from datetime import datetime, timedelta, UTC
from typing import cast
from unittest.mock import MagicMock

import pytest
from pytest import MonkeyPatch
from freezegun import freeze_time

from cloudshortener.types import LambdaEvent, LambdaContext, LambdaConfiguration
from cloudshortener.lambdas.redirect_url import app
from cloudshortener.models import ShortURLModel
from cloudshortener.dao.base import ShortURLBaseDAO
from cloudshortener.dao.exceptions import ShortURLNotFoundError


@pytest.fixture
def apigw_event() -> LambdaEvent:
    return cast(LambdaEvent, {
        'resource': '/{shortcode}',
        'requestContext': {'resourcePath': '/{shortcode}', 'httpMethod': 'GET'},
        'pathParameters': {'apigw': 'event'},
        'httpMethod': 'GET',
        'path': '/abc123',
        'requestContext': {'domainName': 'testhost:1000', 'stage': 'test'},
    })


@pytest.fixture
def successful_event_302() -> LambdaEvent:
    return cast(LambdaEvent, {
        'resource': '/{shortcode}',
        'requestContext': {'resourcePath': '/{shortcode}', 'httpMethod': 'GET'},
        'pathParameters': {'shortcode': 'abc123'},
        'httpMethod': 'GET',
        'path': '/abc123',
        'requestContext': {'domainName': 'testhost:1000', 'stage': 'test'},
    })


@pytest.fixture
def bad_request_400() -> LambdaEvent:
    return cast(LambdaEvent, {
        'resource': '/{shortcode}',
        'requestContext': {'resourcePath': '/{shortcode}', 'httpMethod': 'GET'},
        'pathParameters': {'invalid': 'path'},
        'httpMethod': 'GET',
        'path': '/abc123',
        'requestContext': {'domainName': 'testhost:1000', 'stage': 'test'},
    })


class TestRedirectUrlHandler:

    @pytest.fixture
    def context(self) -> LambdaContext:
        return cast(LambdaContext, {'function_name': 'redirect_url'})

    @pytest.fixture
    def config(self) -> LambdaConfiguration:
        return cast(LambdaConfiguration, {'redis': {'host': 'redis.test', 'port': 6379, 'db': 0}})

    @pytest.fixture
    def short_url_dao(self) -> ShortURLBaseDAO:
        dao = MagicMock(spec=ShortURLBaseDAO)
        dao.get.return_value = ShortURLModel(
            target='https://example.com/blog/chuck-norris-is-awesome',
            shortcode='abc123',
            hits=10000,
            expires_at=datetime.now(UTC) + timedelta(days=10),
        )
        dao.hit.return_value = 9999  # Default: quota not exceeded
        return dao

    @pytest.fixture(autouse=True)
    def setup(
        self,
        monkeypatch: MonkeyPatch,
        context: LambdaContext,
        config: LambdaConfiguration,
        short_url_dao: ShortURLBaseDAO,
    ) -> None:
        # Patch Lambda dependencies
        monkeypatch.setattr(app, 'load_config', lambda *a, **kw: config)
        monkeypatch.setattr(app, 'ShortURLRedisDAO', lambda *a, **kw: short_url_dao)

        self.context = context
        self.config = config
        self.short_url_dao = short_url_dao

    def test_lambda_handler(self, successful_event_302: LambdaEvent) -> None:
        response = app.lambda_handler(successful_event_302, self.context)
        headers = response['headers']
        body = json.loads(response['body'])

        # Assert Lambda successfully redirects user to target URL
        assert response['statusCode'] == 302
        assert body == {}
        assert headers['Location'] == 'https://example.com/blog/chuck-norris-is-awesome'

        # Assert short URL link quota was hit
        self.short_url_dao.hit.assert_called_once_with(shortcode='abc123')
        self.short_url_dao.get.assert_called_once_with(shortcode='abc123')

    def test_lambda_handler_with_invalid_path_parameters(self, bad_request_400: LambdaEvent) -> None:
        response = app.lambda_handler(bad_request_400, self.context)
        body = json.loads(response['body'])

        assert response['statusCode'] == 400
        assert body['message'] == "Bad Request (missing 'shortcode' in path)"
        assert body['errorCode'] == 'MISSING_SHORTCODE'

    def test_lambda_handler_with_invalid_shortcode(self, successful_event_302: LambdaEvent) -> None:
        # Ensure the DAO raises ShortURLNotFoundError on hit()
        self.short_url_dao.hit.side_effect = ShortURLNotFoundError()
        short_url = 'https://testhost:1000/abc123'

        response = app.lambda_handler(successful_event_302, self.context)
        body = json.loads(response['body'])

        assert response['statusCode'] == 400
        assert body['message'] == f"Bad Request (short url {short_url} doesn't exist)"
        assert body['errorCode'] == 'SHORT_URL_NOT_FOUND'
        self.short_url_dao.hit.assert_called_once_with(shortcode='abc123')
        self.short_url_dao.get.assert_not_called()

    @freeze_time('2025-10-15')
    def test_lambda_handler_with_exceeded_quota(self, successful_event_302: LambdaEvent) -> None:
        self.short_url_dao.hit.return_value = -1  # Quota exceeded

        response = app.lambda_handler(successful_event_302, self.context)
        body = json.loads(response['body'])
        headers = response['headers']

        assert response['statusCode'] == 429
        assert headers['Content-Type'] == 'application/json'
        assert 'Retry-After' in headers
        assert body['errorCode'] == 'LINK_QUOTA_EXCEEDED'
        assert 'Monthly hit quota exceeded for link' in body['message']
        assert '2025-11-01T00:00:00Z' in body['message']
        self.short_url_dao.hit.assert_called_once_with(shortcode='abc123')
        self.short_url_dao.get.assert_not_called()

    @freeze_time('2025-10-15')
    def test_lambda_handler_with_multiple_quota_exceeded_requests(self, successful_event_302: LambdaEvent) -> None:
        self.short_url_dao.hit.return_value = -5  # Quota exceeded

        # First request
        response1 = app.lambda_handler(successful_event_302, self.context)
        body1 = json.loads(response1['body'])

        assert response1['statusCode'] == 429
        assert body1['errorCode'] == 'LINK_QUOTA_EXCEEDED'

        # Second request (quota still exceeded)
        response2 = app.lambda_handler(successful_event_302, self.context)
        body2 = json.loads(response2['body'])

        assert response2['statusCode'] == 429
        assert body2['errorCode'] == 'LINK_QUOTA_EXCEEDED'

        # Third request (quota still exceeded)
        response3 = app.lambda_handler(successful_event_302, self.context)
        body3 = json.loads(response3['body'])

        assert response3['statusCode'] == 429
        assert body3['errorCode'] == 'LINK_QUOTA_EXCEEDED'

        # Verify hit() was called for each request
        assert self.short_url_dao.hit.call_count == 3
        self.short_url_dao.get.assert_not_called()

    def test_lambda_handler_with_invalid_configuration_file(
        self,
        monkeypatch: MonkeyPatch,
        apigw_event: LambdaEvent,
    ) -> None:
        mock_load_config = MagicMock(side_effect=FileNotFoundError('Something goes wrong'))
        monkeypatch.setattr(app, 'load_config', mock_load_config)

        response = app.lambda_handler(apigw_event, self.context)
        body = json.loads(response['body'])

        assert response['statusCode'] == 500
        assert body['message'] == 'Internal Server Error'
