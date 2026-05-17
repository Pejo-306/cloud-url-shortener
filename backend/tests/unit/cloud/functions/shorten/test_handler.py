import json
from unittest.mock import MagicMock

import pytest
from pytest import MonkeyPatch

from cloudshortener.cloud.functions.shorten import handler as handler_module
from cloudshortener.cloud.functions.shorten.constants import (
    INVALID_JSON,
    LINK_QUOTA_EXCEEDED,
    MISSING_TARGET_URL,
    MISSING_USER_ID,
    SHORT_URL_ALREADY_EXISTS,
)
from cloudshortener.cloud.functions.types import ShortenConfig, ShortenRequest
from cloudshortener.constants import UNKNOWN_INTERNAL_SERVER_ERROR, DefaultQuota
from cloudshortener.dao.base import ShortURLBaseDAO, UserBaseDAO
from cloudshortener.dao.exceptions import ShortURLAlreadyExistsError
from cloudshortener.models import ShortURLModel
from cloudshortener.types import HttpHeaders
from tests.unit.helpers import monkeypatch_innermost_function


class TestShortenHandler:
    short_url_dao: ShortURLBaseDAO
    user_dao: UserBaseDAO

    @pytest.fixture
    def shorten_config(self) -> ShortenConfig:
        return ShortenConfig(
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
        dao.count.return_value = 42
        return dao

    @pytest.fixture
    def user_dao(self) -> UserBaseDAO:
        dao = MagicMock(spec=UserBaseDAO)
        dao.quota.return_value = 10
        dao.increment_quota.return_value = 11
        return dao

    @pytest.fixture(autouse=True)
    def setup(self, monkeypatch: MonkeyPatch, short_url_dao: ShortURLBaseDAO, user_dao: UserBaseDAO) -> None:
        monkeypatch.setattr(handler_module, 'ShortURLRedisDAO', lambda *a, **kw: short_url_dao)
        monkeypatch.setattr(handler_module, 'UserRedisDAO', lambda *a, **kw: user_dao)
        monkeypatch.setattr(handler_module, 'generate_shortcode', lambda *a, **kw: 'abc123')
        self.short_url_dao = short_url_dao
        self.user_dao = user_dao

    def assert_has_cors_headers(self, headers: HttpHeaders) -> None:
        assert headers['Access-Control-Allow-Origin'] == '*'  # TODO: this should be a specific frontend domain only
        assert headers['Access-Control-Allow-Headers'] == 'Authorization,Content-Type'
        assert headers['Access-Control-Allow-Methods'] == 'OPTIONS,POST,GET'

    def test_shorten_success(self, shorten_config: ShortenConfig) -> None:
        target_url = 'https://example.com/blog/chuck-norris-is-awesome'
        body = json.dumps({'targetUrl': target_url})
        req = ShortenRequest(user_id='user123', body=body, base_url='https://testhost')

        result = handler_module.shorten(req, shorten_config)
        parsed = json.loads(result.body)

        # Assert function successfully shortens the target URL
        assert result.status_code == 200
        assert parsed['message'] == f'Successfully shortened {target_url} to https://testhost/abc123'
        assert parsed['targetUrl'] == target_url
        assert parsed['shortUrl'] == 'https://testhost/abc123'
        assert parsed['shortcode'] == 'abc123'
        assert parsed['userQuota'] == 11
        assert parsed['remainingQuota'] == DefaultQuota.LINK_GENERATION - 11

        # Assert CORS headers
        self.assert_has_cors_headers(result.headers)

        # Assert DAO operations
        short_url = ShortURLModel(target=target_url, shortcode='abc123')
        self.short_url_dao.count.assert_called_once_with(increment=True)
        self.short_url_dao.insert.assert_called_once_with(short_url=short_url)
        self.user_dao.quota.assert_called_once_with(user_id='user123')
        self.user_dao.increment_quota.assert_called_once_with(user_id='user123')

    def test_shorten_with_missing_user_id(self, shorten_config: ShortenConfig) -> None:
        req = ShortenRequest(user_id=None, body=json.dumps({'targetUrl': 'https://example.com'}), base_url='https://host')

        result = handler_module.shorten(req, shorten_config)
        body = json.loads(result.body)

        assert result.status_code == 401
        assert body['message'] == "Unauthorized (missing 'sub' in JWT claims)"
        assert body['errorCode'] == MISSING_USER_ID
        self.assert_has_cors_headers(result.headers)

    def test_shorten_with_invalid_json_body(self, shorten_config: ShortenConfig) -> None:
        req = ShortenRequest(user_id='user123', body='{"invalid_json": true', base_url='https://host')

        result = handler_module.shorten(req, shorten_config)
        body = json.loads(result.body)

        assert result.status_code == 400
        assert body['message'] == 'Bad Request (invalid JSON body)'
        assert body['errorCode'] == INVALID_JSON
        self.assert_has_cors_headers(result.headers)

    def test_shorten_with_missing_target_url(self, shorten_config: ShortenConfig) -> None:
        req = ShortenRequest(user_id='user123', body=json.dumps({'foo': True}), base_url='https://host')

        result = handler_module.shorten(req, shorten_config)
        body = json.loads(result.body)

        assert result.status_code == 400
        assert body['message'] == "Bad Request (missing 'targetUrl' in JSON body)"
        assert body['errorCode'] == MISSING_TARGET_URL
        self.assert_has_cors_headers(result.headers)

    def test_shorten_with_quota_exceeded(self, monkeypatch: MonkeyPatch, shorten_config: ShortenConfig) -> None:
        class BiggerQuota:
            LINK_HITS = DefaultQuota.LINK_HITS
            LINK_GENERATION = 30

        monkeypatch.setattr(handler_module, 'DefaultQuota', BiggerQuota)
        self.user_dao.quota.return_value = 30

        req = ShortenRequest(
            user_id='user123',
            body=json.dumps({'targetUrl': 'https://example.com'}),
            base_url='https://host',
        )

        result = handler_module.shorten(req, shorten_config)
        body = json.loads(result.body)

        assert result.status_code == 429
        assert body['message'] == 'Too Many Link Generation Requests (monthly quota reached)'
        assert body['errorCode'] == LINK_QUOTA_EXCEEDED
        self.assert_has_cors_headers(result.headers)

    def test_shorten_with_existing_short_url(self, shorten_config: ShortenConfig) -> None:
        # Assert Short URL DAO won't override an existing short URL
        self.short_url_dao.insert.side_effect = ShortURLAlreadyExistsError()

        req = ShortenRequest(
            user_id='user123',
            body=json.dumps({'targetUrl': 'https://example.com'}),
            base_url='https://host',
        )

        result = handler_module.shorten(req, shorten_config)
        body = json.loads(result.body)

        assert result.status_code == 409
        assert body['message'] == 'Conflict (short URL already exists)'
        assert body['errorCode'] == SHORT_URL_ALREADY_EXISTS
        self.assert_has_cors_headers(result.headers)

    def test_shorten_with_unhandled_exception(self, monkeypatch: MonkeyPatch, shorten_config: ShortenConfig) -> None:
        def failing_shorten_handler(_request: ShortenRequest, _config: ShortenConfig) -> None:
            raise RuntimeError('unexpected')

        monkeypatch_innermost_function(monkeypatch, handler_module.shorten, failing_shorten_handler)

        req = ShortenRequest(
            user_id='user123',
            body=json.dumps({'targetUrl': 'https://example.com'}),
            base_url='https://host',
        )

        result = handler_module.shorten(req, shorten_config)
        body = json.loads(result.body)

        assert result.status_code == 500
        assert body['message'] == 'Internal Server Error'
        assert body['error_code'] == UNKNOWN_INTERNAL_SERVER_ERROR
