import json
from datetime import UTC, datetime, timedelta
from unittest.mock import MagicMock

import pytest
from freezegun import freeze_time
from pytest import MonkeyPatch

from cloudshortener.cloud.functions.redirect import handler as handler_module
from cloudshortener.cloud.functions.redirect.constants import LINK_QUOTA_EXCEEDED, MISSING_SHORTCODE, SHORT_URL_NOT_FOUND
from cloudshortener.cloud.functions.types import RedirectConfig, RedirectRequest
from cloudshortener.constants import UNKNOWN_INTERNAL_SERVER_ERROR
from cloudshortener.dao.base import ShortURLBaseDAO
from cloudshortener.dao.exceptions import ShortURLNotFoundError
from cloudshortener.models import ShortURLModel
from cloudshortener.types import HttpHeaders
from tests.unit.helpers import monkeypatch_innermost_function


class TestRedirectHandler:
    short_url_dao: ShortURLBaseDAO

    @pytest.fixture
    def redirect_config(self) -> RedirectConfig:
        return RedirectConfig(
            redis_host='redis.test',
            redis_port=6379,
            redis_db=0,
            redis_username=None,
            redis_password=None,
            app_prefix='test:local',
        )

    @pytest.fixture
    def short_url_dao(self) -> ShortURLBaseDAO:
        dao = MagicMock(spec=ShortURLBaseDAO)
        dao.get.return_value = ShortURLModel(
            target='https://example.com/blog/chuck-norris-is-awesome',
            shortcode='abc123',
            hits=10000,
            expires_at=datetime.now(UTC) + timedelta(days=10),
        )
        dao.hit.return_value = 9999
        return dao

    @pytest.fixture(autouse=True)
    def setup(self, monkeypatch: MonkeyPatch, short_url_dao: ShortURLBaseDAO) -> None:
        monkeypatch.setattr(handler_module, 'ShortURLRedisDAO', lambda *a, **kw: short_url_dao)
        self.short_url_dao = short_url_dao

    def assert_has_cors_headers(self, headers: HttpHeaders) -> None:
        assert headers['Access-Control-Allow-Origin'] == '*'  # TODO: this should be a specific frontend domain only
        assert headers['Access-Control-Allow-Headers'] == 'Content-Type'
        assert headers['Access-Control-Allow-Methods'] == 'OPTIONS,POST,GET'

    def test_redirect_success(self, redirect_config: RedirectConfig) -> None:
        req = RedirectRequest(shortcode='abc123', short_url='https://testhost/abc123')
        result = handler_module.redirect(req, redirect_config)

        # Assert redirect function successfully redirects user to target URL
        assert result.status_code == 302
        assert json.loads(result.body) == {}
        assert result.headers['Location'] == 'https://example.com/blog/chuck-norris-is-awesome'

        # Assert CORS headers
        self.assert_has_cors_headers(result.headers)

        # Assert short URL link quota was hit
        self.short_url_dao.hit.assert_called_once_with(shortcode='abc123')
        self.short_url_dao.get.assert_called_once_with(shortcode='abc123')

    def test_redirect_with_missing_shortcode(self, redirect_config: RedirectConfig) -> None:
        req = RedirectRequest(shortcode=None, short_url='https://testhost')
        result = handler_module.redirect(req, redirect_config)
        body = json.loads(result.body)

        assert result.status_code == 400
        assert body['message'] == "Bad Request (missing 'shortcode' in path)"
        assert body['errorCode'] == MISSING_SHORTCODE
        self.assert_has_cors_headers(result.headers)

        self.short_url_dao.hit.assert_not_called()
        self.short_url_dao.get.assert_not_called()

    def test_redirect_with_invalid_shortcode(self, redirect_config: RedirectConfig) -> None:
        self.short_url_dao.hit.side_effect = ShortURLNotFoundError()

        req = RedirectRequest(shortcode='abc123', short_url='https://testhost/abc123')
        result = handler_module.redirect(req, redirect_config)
        body = json.loads(result.body)

        assert result.status_code == 404
        assert body['message'] == "Not Found (short url https://testhost/abc123 doesn't exist)"
        assert body['errorCode'] == SHORT_URL_NOT_FOUND
        self.assert_has_cors_headers(result.headers)

        self.short_url_dao.hit.assert_called_once_with(shortcode='abc123')
        self.short_url_dao.get.assert_not_called()

    @freeze_time('2025-10-15')
    def test_redirect_with_exceeded_quota(self, redirect_config: RedirectConfig) -> None:
        self.short_url_dao.hit.return_value = -1

        req = RedirectRequest(shortcode='abc123', short_url='https://testhost/abc123')
        result = handler_module.redirect(req, redirect_config)
        body = json.loads(result.body)
        headers = result.headers

        assert result.status_code == 429
        assert headers['Content-Type'] == 'application/json'
        assert 'Retry-After' in headers
        assert body['errorCode'] == LINK_QUOTA_EXCEEDED
        assert body['message'] == 'Monthly hit quota exceeded for link. Try again after 2025-11-01T00:00:00Z.'
        self.assert_has_cors_headers(headers)

        self.short_url_dao.hit.assert_called_once_with(shortcode='abc123')
        self.short_url_dao.get.assert_not_called()

    @freeze_time('2025-10-15')
    def test_redirect_with_multiple_quota_exceeded_requests(self, redirect_config: RedirectConfig) -> None:
        self.short_url_dao.hit.return_value = -5  # Quota exceeded
        req = RedirectRequest(shortcode='abc123', short_url='https://testhost/abc123')

        # First request
        response1 = handler_module.redirect(req, redirect_config)
        body1 = json.loads(response1.body)

        assert response1.status_code == 429
        assert body1['errorCode'] == LINK_QUOTA_EXCEEDED

        # Second request (quota still exceeded)
        response2 = handler_module.redirect(req, redirect_config)
        body2 = json.loads(response2.body)

        assert response2.status_code == 429
        assert body2['errorCode'] == LINK_QUOTA_EXCEEDED

        # Third request (quota still exceeded)
        response3 = handler_module.redirect(req, redirect_config)
        body3 = json.loads(response3.body)

        assert response3.status_code == 429
        assert body3['errorCode'] == LINK_QUOTA_EXCEEDED

        # Verify hit() was called for each request
        assert self.short_url_dao.hit.call_count == 3
        self.short_url_dao.get.assert_not_called()

    def test_redirect_with_unhandled_exception(self, monkeypatch: MonkeyPatch, redirect_config: RedirectConfig) -> None:
        def failing_redirect_handler(_request: RedirectRequest, _config: RedirectConfig) -> None:
            raise RuntimeError('unexpected')

        monkeypatch_innermost_function(monkeypatch, handler_module.redirect, failing_redirect_handler)

        req = RedirectRequest(shortcode='abc123', short_url='https://testhost/abc123')
        result = handler_module.redirect(req, redirect_config)
        body = json.loads(result.body)

        assert result.status_code == 500
        assert body['message'] == 'Internal Server Error'
        assert body['error_code'] == UNKNOWN_INTERNAL_SERVER_ERROR
