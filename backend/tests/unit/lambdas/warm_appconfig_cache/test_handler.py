import json
from unittest.mock import MagicMock

import pytest
from pytest import MonkeyPatch

from cloudshortener.types import LambdaEvent
from cloudshortener.dao.cache import AppConfigCacheDAO
from cloudshortener.dao.exceptions import CacheMissError, CachePutError, DataStoreError
from cloudshortener.lambdas.warm_appconfig_cache import app


class TestWarmAppConfigCache:
    @pytest.fixture
    def event(self) -> LambdaEvent:
        return {
            'source': 'aws.appconfig',
            'detail-type': 'AppConfig Deployment Complete',
            'detail': {},
        }

    @pytest.fixture
    def cache_dao(self, monkeypatch: MonkeyPatch) -> AppConfigCacheDAO:
        cache_dao = MagicMock(spec=AppConfigCacheDAO)
        cache_dao.version.return_value = 1
        cache_dao.latest.return_value = {
            'build': 42,
            'active_backend': 'redis',
            'configs': {
                'shorten_url': {
                    'redis': {
                        'host': 'redis.test',
                        'port': 6379,
                        'db': 0,
                    },
                },
            },
        }
        monkeypatch.setattr(app, 'AppConfigCacheDAO', lambda *a, **kw: cache_dao)
        return cache_dao

    def test_lambda_handler_warms_cache(self, event: LambdaEvent, cache_dao: AppConfigCacheDAO):
        result = json.loads(app.lambda_handler(event, None))

        assert result['status'] == 'success'
        assert result['appconfig_version'] == 1
        assert result['message'] == 'Successfully warmed cache with AppConfig version 1'

    @pytest.mark.parametrize(
        'exception, expected_reason, expected_error',
        [
            (CacheMissError('cache miss'), 'cache miss', 'CacheMissError'),
            (CachePutError('cache write failed'), 'cache write failed', 'CachePutError'),
            (DataStoreError('redis unavailable'), 'redis unavailable', 'DataStoreError'),
        ],
    )
    def test_lambda_handler_propagates_cache_errors(
        self,
        event: LambdaEvent,
        cache_dao: AppConfigCacheDAO,
        exception: Exception,
        expected_reason: str,
        expected_error: str,
    ):
        cache_dao.version.side_effect = exception

        result = json.loads(app.lambda_handler(event, None))

        assert result['status'] == 'error'
        assert result['message'] == 'Failed to warm up cache with latest AppConfig'
        assert result['reason'] == expected_reason
        assert result['error'] == expected_error
