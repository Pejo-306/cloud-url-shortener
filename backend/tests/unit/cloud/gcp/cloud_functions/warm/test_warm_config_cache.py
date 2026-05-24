import json
from unittest.mock import Mock

import pytest
from cloudevents.http import CloudEvent
from pytest import MonkeyPatch

from cloudshortener.cloud.functions.types import HttpResponse, WarmConfigCacheConfig, WarmConfigCacheRequest
from cloudshortener.cloud.gcp.dao.cache.gcp_backend_config_cache_dao import GCPBackendConfigCacheDAO
from cloudshortener.cloud.gcp.cloud_functions.warm import main as main_module


class TestGcpWarmConfigCache:
    cloud_event: CloudEvent
    warm_response: HttpResponse

    @pytest.fixture
    def cloud_event(self) -> CloudEvent:
        return CloudEvent(
            {
                'type': 'google.cloud.storage.object.v1.finalized',
                'source': '//storage.googleapis.com/projects/_/buckets/config-bucket',
                'id': 'event-1',
            },
            {
                'bucket': 'config-bucket',
                'name': 'backend-config.json',
            },
        )

    @pytest.fixture
    def warm_response(self) -> HttpResponse:
        return HttpResponse(
            status_code=200,
            body=json.dumps({'status': 'success', 'config_version': 3}),
            headers={'Content-Type': 'application/json'},
        )

    def test_warm_config_cache(
        self,
        monkeypatch: MonkeyPatch,
        cloud_event: CloudEvent,
        warm_response: HttpResponse,
    ) -> None:
        mock_dao = Mock(spec=GCPBackendConfigCacheDAO)
        mock_dao_class = Mock(return_value=mock_dao)
        mock_handler = Mock(return_value=warm_response)
        monkeypatch.setattr(main_module, 'GCPBackendConfigCacheDAO', mock_dao_class)
        monkeypatch.setattr(main_module, 'warm', mock_handler)
        monkeypatch.setattr(main_module, 'app_prefix', lambda: 'app:dev')

        main_module.warm_config_cache(cloud_event)

        mock_dao_class.assert_called_once_with(prefix='app:dev')
        mock_handler.assert_called_once_with(WarmConfigCacheRequest(), WarmConfigCacheConfig(dao=mock_dao))
