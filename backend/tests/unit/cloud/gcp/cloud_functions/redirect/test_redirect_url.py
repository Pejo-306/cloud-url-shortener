import json
from unittest.mock import Mock

import pytest
from flask import Request
from pytest import MonkeyPatch

from cloudshortener.cloud.functions.redirect.handler import cors_headers
from cloudshortener.cloud.functions.types import HttpResponse, RedirectConfig, RedirectRequest
from cloudshortener.cloud.gcp.cloud_functions.redirect import main as main_module
from cloudshortener.constants import FunctionName


class TestGcpRedirectUrl:
    @pytest.fixture
    def options_request(self) -> Request:
        req = Mock(spec=Request)
        req.method = 'OPTIONS'
        return req

    @pytest.fixture
    def redirect_request(self) -> Request:
        req = Mock(spec=Request)
        req.method = 'GET'
        req.path = '/abc123'
        req.host_url = 'https://host/'
        return req

    @pytest.fixture
    def redirect_config(self) -> dict:
        return {'redis': {'host': 'h', 'port': 6379, 'db': 0}}

    @pytest.fixture
    def redirect_response(self) -> HttpResponse:
        return HttpResponse(
            status_code=302,
            body=json.dumps({}),
            headers={
                **cors_headers(),
                'Location': 'https://example.com/target',
            },
        )

    def test_redirect_url_with_options(self, options_request: Request) -> None:
        body, status, headers = main_module.redirect_url(options_request)

        assert status == 204
        assert body == ''
        assert headers == cors_headers()

    def test_redirect_url(
        self,
        monkeypatch: MonkeyPatch,
        redirect_request: Request,
        redirect_config: dict,
        redirect_response: HttpResponse,
    ) -> None:
        expected_redirect_config = RedirectConfig(
            redis_host='h',
            redis_port=6379,
            redis_db=0,
            redis_username=None,
            redis_password=None,
            app_prefix='t:local',
        )
        mock_load = Mock(spec=main_module.load_config, return_value=redirect_config)
        mock_redirect = Mock(spec=main_module.redirect, return_value=redirect_response)
        monkeypatch.setattr(main_module, 'load_config', mock_load)
        monkeypatch.setattr(main_module, 'redirect', mock_redirect)
        monkeypatch.setattr(main_module, 'app_prefix', lambda: 't:local')

        body, status, headers = main_module.redirect_url(redirect_request)

        assert status == redirect_response.status_code
        assert body == redirect_response.body
        assert headers == redirect_response.headers

        mock_load.assert_called_once_with(FunctionName.REDIRECT_URL)
        mock_redirect.assert_called_once_with(
            RedirectRequest(shortcode='abc123', short_url='https://host/abc123'),
            expected_redirect_config,
        )

    def test_redirect_url_with_config_load_error(self, monkeypatch: MonkeyPatch, redirect_request: Request) -> None:
        mock_load = Mock(spec=main_module.load_config, side_effect=RuntimeError('gcs'))
        mock_redirect = Mock(spec=main_module.redirect)
        monkeypatch.setattr(main_module, 'load_config', mock_load)
        monkeypatch.setattr(main_module, 'redirect', mock_redirect)

        body, status, headers = main_module.redirect_url(redirect_request)

        assert status == 500
        assert json.loads(body) == {'message': 'Internal Server Error'}
        assert headers['Content-Type'] == 'application/json'

        assert headers['Access-Control-Allow-Origin'] == '*'
        assert headers['Access-Control-Allow-Headers'] == 'Content-Type'
        assert headers['Access-Control-Allow-Methods'] == 'OPTIONS,POST,GET'

        mock_redirect.assert_not_called()
