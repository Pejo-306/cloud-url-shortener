import time
import json

from tests.integration.gcp.components import Infrastructure, GcpProject
from tests.integration.gcp.constants import BACKEND_CONFIG_WARMING_WAIT_TIME
from tests.integration.gcp.schemas import cache_key_schema


class TestBackendConfigWarming:
    def test_cache_warming_on_backend_config_upload(self, infra: Infrastructure, project: GcpProject):
        # 1. Connect to MemoryStore
        # 2. Find current backend config version
        # 3. Upload a new backend config version
        # 4. Wait for cache warming to finish
        # 5. Assert there's a new versioned backend config document
        # 6. Assert the latest backend config document is the new versioned document
        redis_client = infra.memorystore.redis
        key_schema = cache_key_schema(project)

        current_metadata_key = key_schema.appconfig_latest_metadata_key()
        current_metadata = json.loads(redis_client.get(current_metadata_key))
        current_version = current_metadata['version']

        infra.config.upload_new_backend_config_version()
        # Wait for warm backend config function to finish
        # TODO: we need to implement a max 300s flat polling loop to wait for the function to finish, poll every 10-15s
        time.sleep(BACKEND_CONFIG_WARMING_WAIT_TIME)

        new_backend_config_version_key = key_schema.appconfig_version_key(current_version + 1)
        new_backend_config_version_document = json.loads(redis_client.get(new_backend_config_version_key))
        latest_backend_config_key = key_schema.appconfig_latest_key()
        latest_backend_config_document = json.loads(redis_client.get(latest_backend_config_key))
        assert new_backend_config_version_document == latest_backend_config_document
