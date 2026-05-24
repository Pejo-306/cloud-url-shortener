import json
from typing import cast
from unittest.mock import MagicMock, call

import pytest
import redis

from cloudshortener.cloud.dao.base.backend_config_cache_base_dao import BackendConfigCacheBaseDAO
from cloudshortener.cloud.dao.cache.cache_key_schema import CacheKeySchema
from cloudshortener.cloud.dao.cache.constants import CacheTTL
from cloudshortener.dao.exceptions import CacheMissError, CachePutError
from cloudshortener.types import BackendConfig, BackendConfigMetadata


class ConcreteBackendConfigCacheDAO(BackendConfigCacheBaseDAO):
    source_data: tuple[int, BackendConfig, BackendConfigMetadata]

    def __init__(self, redis_client: redis.Redis, prefix: str | None = None, ttl: int | None = CacheTTL.COOL):
        self.redis = redis_client
        self.keys = CacheKeySchema(prefix=prefix)
        self.ttl = ttl

    def _fetch_from_source(self) -> tuple[int, BackendConfig, BackendConfigMetadata]:
        return self.source_data


class TestBackendConfigCacheBaseDAO:
    app_prefix: str
    default_config_doc: BackendConfig
    default_config_metadata: BackendConfigMetadata
    dao: ConcreteBackendConfigCacheDAO
    redis_client: redis.Redis

    @pytest.fixture
    def app_prefix(self) -> str:
        return 'testapp:test'

    @pytest.fixture
    def default_config_doc(self) -> BackendConfig:
        return cast(
            BackendConfig,
            {
                'build': 42,
                'active_backend': 'redis',
                'configs': {
                    'shorten_url': {
                        'redis': {
                            'host': 'localtest',
                            'port': 96379,
                            'db': 42,
                        }
                    },
                    'redirect_url': {
                        'redis': {
                            'host': 'localtest',
                            'port': 66379,
                            'db': 24,
                        }
                    },
                },
            },
        )

    @pytest.fixture
    def default_config_metadata(self) -> BackendConfigMetadata:
        return cast(
            BackendConfigMetadata,
            {
                'version': 42,
                'etag': 'W/"etag-latest"',
                'content_type': 'application/json',
                'fetched_at': '2025-01-03T00:00:00+00:00',
            },
        )

    @pytest.fixture
    def redis_client(self) -> redis.Redis:
        """Mock a Redis pipeline-compatible client."""
        client = MagicMock(spec=redis.client.Pipeline)
        client.connection_pool = MagicMock(
            spec=redis.ConnectionPool,
            connection_kwargs={'host': 'redis.test', 'port': 6379, 'db': 0},
        )
        client.exists.return_value = False
        client.pipeline.return_value = client
        client.__enter__.return_value = client
        client.__exit__.return_value = None
        client.get.return_value = None
        return cast(redis.Redis, client)

    @pytest.fixture
    def dao(
        self,
        redis_client: redis.Redis,
        app_prefix: str,
        default_config_doc: BackendConfig,
        default_config_metadata: BackendConfigMetadata,
    ) -> ConcreteBackendConfigCacheDAO:
        _dao = ConcreteBackendConfigCacheDAO(redis_client=redis_client, prefix=app_prefix, ttl=CacheTTL.COOL)
        _dao.source_data = (42, default_config_doc, default_config_metadata)
        return _dao

    @pytest.fixture(autouse=True)
    def setup(self, dao: ConcreteBackendConfigCacheDAO, redis_client: redis.Redis) -> None:
        self.dao = dao
        self.redis_client = redis_client

    def test_latest_cache_hit_returns_document(self, default_config_doc: BackendConfig):
        self.redis_client.get.return_value = json.dumps(default_config_doc)

        result = self.dao.latest(pull=False)

        assert isinstance(result, dict)
        assert result['build'] == 42
        assert result['active_backend'] == 'redis'
        assert result['configs']['shorten_url']['redis']['host'] == 'localtest'
        assert result['configs']['shorten_url']['redis']['port'] == 96379
        assert result['configs']['shorten_url']['redis']['db'] == 42
        assert result['configs']['redirect_url']['redis']['host'] == 'localtest'
        assert result['configs']['redirect_url']['redis']['port'] == 66379
        assert result['configs']['redirect_url']['redis']['db'] == 24

        self.redis_client.get.assert_called_once_with('cache:testapp:test:appconfig:latest')

    def test_latest_cache_miss_with_pull_false_raises(self):
        self.redis_client.get.return_value = None
        with pytest.raises(CacheMissError, match='latest'):
            self.dao.latest(pull=False)

    def test_latest_cache_miss_with_pull_true_fetches_and_writes(
        self,
        default_config_doc: BackendConfig,
        default_config_metadata: BackendConfigMetadata,
    ):
        # fmt: off
        expected_calls = [
            call('cache:testapp:test:appconfig:v42', json.dumps(default_config_doc, separators=(',', ':'), ensure_ascii=False), ex=CacheTTL.COOL),
            call('cache:testapp:test:appconfig:v42:metadata', json.dumps(default_config_metadata, separators=(',', ':'), ensure_ascii=False), ex=CacheTTL.COOL),
            call('cache:testapp:test:appconfig:latest', json.dumps(default_config_doc, separators=(',', ':'), ensure_ascii=False), ex=CacheTTL.COOL),
            call('cache:testapp:test:appconfig:latest:metadata', json.dumps(default_config_metadata, separators=(',', ':'), ensure_ascii=False), ex=CacheTTL.COOL),
        ]
        # fmt: on
        self.redis_client.get.return_value = None

        result = self.dao.latest(pull=True)

        assert isinstance(result, dict)
        assert result['build'] == 42
        assert result['active_backend'] == 'redis'
        assert result['configs']['shorten_url']['redis']['host'] == 'localtest'
        assert result['configs']['shorten_url']['redis']['port'] == 96379
        assert result['configs']['shorten_url']['redis']['db'] == 42
        assert result['configs']['redirect_url']['redis']['host'] == 'localtest'
        assert result['configs']['redirect_url']['redis']['port'] == 66379
        assert result['configs']['redirect_url']['redis']['db'] == 24

        assert self.redis_client.set.call_count == 4
        self.redis_client.set.assert_has_calls(expected_calls)
        self.redis_client.execute.assert_called_once()

    def test_get_version_cache_hit_returns_document(self, default_config_doc: BackendConfig):
        self.redis_client.get.return_value = json.dumps(default_config_doc)

        result = self.dao.get(42, pull=False)

        assert isinstance(result, dict)
        assert result['build'] == 42
        assert result['active_backend'] == 'redis'
        assert result['configs']['shorten_url']['redis']['host'] == 'localtest'
        assert result['configs']['shorten_url']['redis']['port'] == 96379
        assert result['configs']['shorten_url']['redis']['db'] == 42
        assert result['configs']['redirect_url']['redis']['host'] == 'localtest'
        assert result['configs']['redirect_url']['redis']['port'] == 66379
        assert result['configs']['redirect_url']['redis']['db'] == 24

        self.redis_client.get.assert_called_once_with('cache:testapp:test:appconfig:v42')

    def test_get_version_cache_miss_with_pull_false_raises(self):
        self.redis_client.get.return_value = None
        with pytest.raises(CacheMissError, match='v42'):
            self.dao.get(42, pull=False)

    def test_get_version_cache_miss_with_pull_true_fetches_and_writes(
        self,
        default_config_doc: BackendConfig,
        default_config_metadata: BackendConfigMetadata,
    ):
        written_config_doc = default_config_doc.copy()
        written_config_doc['build'] = 9
        written_config_metadata = default_config_metadata.copy()
        written_config_metadata['version'] = 9
        self.dao.source_data = (9, written_config_doc, written_config_metadata)
        # fmt: off
        expected_calls = [
            call('cache:testapp:test:appconfig:v9', json.dumps(written_config_doc, separators=(',', ':'), ensure_ascii=False), ex=CacheTTL.COOL),
            call('cache:testapp:test:appconfig:v9:metadata', json.dumps(written_config_metadata, separators=(',', ':'), ensure_ascii=False), ex=CacheTTL.COOL),
        ]
        # fmt: on
        self.redis_client.get.return_value = None

        result = self.dao.get(9, pull=True)

        assert isinstance(result, dict)
        assert result['build'] == 9
        assert result['active_backend'] == 'redis'
        assert result['configs']['shorten_url']['redis']['host'] == 'localtest'
        assert result['configs']['shorten_url']['redis']['port'] == 96379
        assert result['configs']['shorten_url']['redis']['db'] == 42
        assert result['configs']['redirect_url']['redis']['host'] == 'localtest'
        assert result['configs']['redirect_url']['redis']['port'] == 66379
        assert result['configs']['redirect_url']['redis']['db'] == 24

        assert self.redis_client.set.call_count == 2
        self.redis_client.set.assert_has_calls(expected_calls)
        self.redis_client.execute.assert_called_once()

    def test_metadata_cache_hit_returns_metadata(self, default_config_metadata):
        self.redis_client.get.return_value = json.dumps(default_config_metadata)

        result = self.dao.metadata(42, pull=False)

        assert isinstance(result, dict)
        assert result['version'] == 42
        assert result['etag'] == 'W/"etag-latest"'
        assert result['content_type'] == 'application/json'
        assert result['fetched_at'] == '2025-01-03T00:00:00+00:00'

        self.redis_client.get.assert_called_once_with('cache:testapp:test:appconfig:v42:metadata')

    def test_metadata_cache_miss_with_pull_false_raises(self):
        self.redis_client.get.return_value = None
        with pytest.raises(CacheMissError, match='metadata'):
            self.dao.metadata(11, pull=False)

    def test_metadata_cache_miss_with_pull_true_fetches_and_writes(
        self,
        default_config_doc: BackendConfig,
        default_config_metadata: BackendConfigMetadata,
    ):
        written_config_doc = default_config_doc.copy()
        written_config_doc['build'] = 9
        written_config_metadata = default_config_metadata.copy()
        written_config_metadata['version'] = 9
        self.dao.source_data = (9, written_config_doc, written_config_metadata)
        # fmt: off
        expected_calls = [
            call('cache:testapp:test:appconfig:v9', json.dumps(written_config_doc, separators=(',', ':'), ensure_ascii=False), ex=CacheTTL.COOL),
            call('cache:testapp:test:appconfig:v9:metadata', json.dumps(written_config_metadata, separators=(',', ':'), ensure_ascii=False), ex=CacheTTL.COOL),
        ]
        # fmt: on
        self.redis_client.get.return_value = None

        result = self.dao.metadata(9, pull=True)

        assert isinstance(result, dict)
        assert result['version'] == 9
        assert result['etag'] == 'W/"etag-latest"'
        assert result['content_type'] == 'application/json'
        assert result['fetched_at'] == '2025-01-03T00:00:00+00:00'

        assert self.redis_client.set.call_count == 2
        self.redis_client.set.assert_has_calls(expected_calls)
        self.redis_client.execute.assert_called_once()

    def test_version_cache_hit_returns_version(self, default_config_metadata: BackendConfigMetadata):
        self.redis_client.get.return_value = json.dumps(default_config_metadata)

        result = self.dao.version(pull=False)
        assert result == 42

        self.redis_client.get.assert_called_once_with('cache:testapp:test:appconfig:latest:metadata')

    def test_version_cache_miss_with_pull_false_raises(self):
        self.redis_client.get.return_value = None
        with pytest.raises(CacheMissError, match='latest'):
            self.dao.version(pull=False)

    def test_version_cache_miss_with_pull_true_fetches_and_writes(
        self,
        default_config_doc: BackendConfig,
        default_config_metadata: BackendConfigMetadata,
    ):
        # fmt: off
        expected_calls = [
            call('cache:testapp:test:appconfig:v42', json.dumps(default_config_doc, separators=(',', ':'), ensure_ascii=False), ex=CacheTTL.COOL),
            call('cache:testapp:test:appconfig:v42:metadata', json.dumps(default_config_metadata, separators=(',', ':'), ensure_ascii=False), ex=CacheTTL.COOL),
            call('cache:testapp:test:appconfig:latest', json.dumps(default_config_doc, separators=(',', ':'), ensure_ascii=False), ex=CacheTTL.COOL),
            call('cache:testapp:test:appconfig:latest:metadata', json.dumps(default_config_metadata, separators=(',', ':'), ensure_ascii=False), ex=CacheTTL.COOL),
        ]
        # fmt: on
        self.redis_client.get.return_value = None

        result = self.dao.version(pull=True)
        assert result == 42

        assert self.redis_client.set.call_count == 4
        self.redis_client.set.assert_has_calls(expected_calls)
        self.redis_client.execute.assert_called_once()

    def test_cache_put_error_when_pipeline_execute_fails(self):
        self.redis_client.get.return_value = None
        self.redis_client.execute.side_effect = redis.exceptions.ConnectionError('Connection error')

        with pytest.raises(CachePutError, match='Failed to write backend config v42'):
            self.dao.get(42, pull=True)

    def test_force_pull_latest(
        self,
        default_config_doc: BackendConfig,
        default_config_metadata: BackendConfigMetadata,
    ):
        self.redis_client.get.return_value = json.dumps({'stale': 'data'})

        # fmt: off
        expected_calls = [
            call('cache:testapp:test:appconfig:v42', json.dumps(default_config_doc, separators=(',', ':'), ensure_ascii=False), ex=CacheTTL.COOL),
            call('cache:testapp:test:appconfig:v42:metadata', json.dumps(default_config_metadata, separators=(',', ':'), ensure_ascii=False), ex=CacheTTL.COOL),
            call('cache:testapp:test:appconfig:latest', json.dumps(default_config_doc, separators=(',', ':'), ensure_ascii=False), ex=CacheTTL.COOL),
            call('cache:testapp:test:appconfig:latest:metadata', json.dumps(default_config_metadata, separators=(',', ':'), ensure_ascii=False), ex=CacheTTL.COOL),
        ]
        # fmt: on

        result = self.dao.latest(force=True)

        assert isinstance(result, dict)
        assert result == default_config_doc
        assert result['build'] == 42
        assert result['active_backend'] == 'redis'
        assert result['configs']['shorten_url']['redis']['host'] == 'localtest'
        assert result['configs']['shorten_url']['redis']['port'] == 96379
        assert result['configs']['shorten_url']['redis']['db'] == 42
        assert result['configs']['redirect_url']['redis']['host'] == 'localtest'
        assert result['configs']['redirect_url']['redis']['port'] == 66379
        assert result['configs']['redirect_url']['redis']['db'] == 24

        self.redis_client.get.assert_not_called()

        assert self.redis_client.set.call_count == 4
        self.redis_client.set.assert_has_calls(expected_calls)
        self.redis_client.execute.assert_called_once()
