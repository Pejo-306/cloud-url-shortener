import json
from unittest.mock import Mock

import pytest
from pytest import MonkeyPatch

from cloudshortener.cloud.dao.base.backend_config_cache_base_dao import BackendConfigCacheBaseDAO
from cloudshortener.cloud.functions.types import WarmConfigCacheConfig, WarmConfigCacheRequest
from cloudshortener.cloud.functions.warm import handler as handler_module
from cloudshortener.cloud.functions.warm.constants import ERROR, SUCCESS
from cloudshortener.dao.exceptions import CachePutError, DataStoreError, DAOError
from tests.unit.helpers import monkeypatch_innermost_function


class TestWarmConfigCacheHandler:
    cache_dao: BackendConfigCacheBaseDAO
    warm_request: WarmConfigCacheRequest
    warm_config: WarmConfigCacheConfig

    @pytest.fixture
    def cache_dao(self) -> BackendConfigCacheBaseDAO:
        dao = Mock(spec=BackendConfigCacheBaseDAO)
        dao.version.return_value = 7
        return dao

    @pytest.fixture
    def warm_request(self) -> WarmConfigCacheRequest:
        return WarmConfigCacheRequest()

    @pytest.fixture
    def warm_config(self, cache_dao: BackendConfigCacheBaseDAO) -> WarmConfigCacheConfig:
        return WarmConfigCacheConfig(dao=cache_dao)

    @pytest.fixture(autouse=True)
    def setup(self, cache_dao: BackendConfigCacheBaseDAO) -> None:
        self.cache_dao = cache_dao

    def test_warm_config_cache_success(
        self,
        warm_request: WarmConfigCacheRequest,
        warm_config: WarmConfigCacheConfig,
    ) -> None:
        result = handler_module.warm(warm_request, warm_config)
        body = json.loads(result.body)

        assert result.status_code == 200
        assert body['status'] == SUCCESS
        assert body['config_version'] == 7
        self.cache_dao.version.assert_called_once_with(force=True)

    @pytest.mark.parametrize(
        ('error', 'expected_error', 'expected_reason'),
        [
            (CachePutError('write failed'), 'CachePutError', 'write failed'),
            (DataStoreError("Can't connect to Redis"), 'DataStoreError', "Can't connect to Redis"),
        ],
    )
    def test_warm_config_cache_with_dao_error(
        self,
        warm_request: WarmConfigCacheRequest,
        warm_config: WarmConfigCacheConfig,
        error: DAOError,
        expected_error: str,
        expected_reason: str,
    ) -> None:
        self.cache_dao.version.side_effect = error

        result = handler_module.warm(warm_request, warm_config)
        body = json.loads(result.body)

        assert result.status_code == 500
        assert body['status'] == ERROR
        assert body['error'] == expected_error
        assert body['reason'] == expected_reason

    def test_warm_config_cache_with_unhandled_exception(
        self,
        monkeypatch: MonkeyPatch,
        warm_request: WarmConfigCacheRequest,
        warm_config: WarmConfigCacheConfig,
    ) -> None:
        def raise_runtime_error(*args, **kwargs):
            raise RuntimeError('boom')

        monkeypatch_innermost_function(monkeypatch, handler_module.warm, raise_runtime_error)

        result = handler_module.warm(warm_request, warm_config)
        body = json.loads(result.body)

        assert result.status_code == 500
        assert body['message'] == 'Internal Server Error'
