import base64
import json
from unittest.mock import Mock

import pytest
from flask import Request
from pytest import MonkeyPatch

from cloudshortener.cloud.functions.shorten.handler import cors_headers
from cloudshortener.cloud.functions.types import HttpResponse, ShortenConfig, ShortenRequest
from cloudshortener.cloud.gcp.cloud_functions.shorten import main as main_module
from cloudshortener.constants import FunctionName


def _encode_userinfo(sub: str) -> str:
    return base64.urlsafe_b64encode(json.dumps({'sub': sub}).encode()).decode().rstrip('=')


class TestGcpShortenUrl:
    @pytest.fixture
    def options_request(self) -> Request:
        req = Mock(spec=Request)
        req.method = 'OPTIONS'
        return req

    @pytest.fixture
    def shorten_request(self) -> Request:
        req = Mock(spec=Request)
        req.method = 'POST'
        req.headers = {'X-Apigateway-Api-Userinfo': _encode_userinfo('user123')}
        req.get_data = Mock(return_value=json.dumps({'targetUrl': 'https://example.com/target'}))
        req.host_url = 'https://host/'
        return req

    @pytest.fixture
    def shorten_config(self) -> dict:
        return {'redis': {'host': 'h', 'port': 6379, 'db': 0}}

    @pytest.fixture
    def shorten_response(self) -> HttpResponse:
        return HttpResponse(
            status_code=200,
            body=json.dumps({'message': 'ok', 'targetUrl': 'https://example.com/target'}),
            headers=cors_headers(),
        )

    def test_shorten_url_with_options(self, options_request: Request) -> None:
        body, status, headers = main_module.shorten_url(options_request)

        assert status == 204
        assert body == ''
        assert headers == cors_headers()

    def test_shorten_url(
        self,
        monkeypatch: MonkeyPatch,
        shorten_request: Request,
        shorten_config: dict,
        shorten_response: HttpResponse,
    ) -> None:
        expected_shorten_config = ShortenConfig(
            redis_host='h',
            redis_port=6379,
            redis_db=0,
            redis_username=None,
            redis_password=None,
            app_prefix='t:local',
        )
        mock_load = Mock(spec=main_module.load_config, return_value=shorten_config)
        mock_shorten = Mock(spec=main_module.shorten, return_value=shorten_response)
        monkeypatch.setattr(main_module, 'load_config', mock_load)
        monkeypatch.setattr(main_module, 'shorten', mock_shorten)
        monkeypatch.setattr(main_module, 'app_prefix', lambda: 't:local')

        body, status, headers = main_module.shorten_url(shorten_request)

        assert status == shorten_response.status_code
        assert body == shorten_response.body
        assert headers == shorten_response.headers

        mock_load.assert_called_once_with(FunctionName.SHORTEN_URL)
        mock_shorten.assert_called_once_with(
            ShortenRequest(
                user_id='user123',
                body=json.dumps({'targetUrl': 'https://example.com/target'}),
                base_url='https://host',
            ),
            expected_shorten_config,
        )

    def test_shorten_url_with_config_load_error(self, monkeypatch: MonkeyPatch, shorten_request: Request) -> None:
        mock_load = Mock(spec=main_module.load_config, side_effect=RuntimeError('gcs'))
        mock_shorten = Mock(spec=main_module.shorten)
        monkeypatch.setattr(main_module, 'load_config', mock_load)
        monkeypatch.setattr(main_module, 'shorten', mock_shorten)

        body, status, headers = main_module.shorten_url(shorten_request)

        assert status == 500
        assert json.loads(body) == {'message': 'Internal Server Error'}
        assert headers['Content-Type'] == 'application/json'

        assert headers['Access-Control-Allow-Origin'] == '*'
        assert headers['Access-Control-Allow-Headers'] == 'Authorization,Content-Type'
        assert headers['Access-Control-Allow-Methods'] == 'OPTIONS,POST,GET'

        mock_shorten.assert_not_called()
