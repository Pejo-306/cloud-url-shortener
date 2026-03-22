import time
import json

from tests.integration.cloudformation import Stacks
from tests.integration.schemas import cache_key_schema
from tests.integration.constants import APPCONFIG_WARMING_WAIT_TIME


class TestAppConfigWarming:
    def test_cache_warming_on_appconfig_deployment(self, stacks: Stacks):
        # 1. Connect to ElastiCache
        # 2. Find current appconfig version
        # 3. Deploy a new appconfig version
        # 4. Wait for baking to finish
        # 5. Wait for cache warming to finish
        # 6. Assert there's a new versioned AppConfig document
        # 7. Assert the latest AppConfig document is the new versioned document
        redis_client = stacks.elasticache.redis
        key_schema = cache_key_schema(stacks.orchestrator)

        current_metadata_key = key_schema.appconfig_latest_metadata_key()
        current_metadata = json.loads(redis_client.get(current_metadata_key))
        current_version = current_metadata['version']

        stacks.appconfig.deploy_new_hosted_configuration_version()
        # Wait for warm appconfig function to finish
        # TODO: we need to implement a max 300s flat polling loop to wait for the function to finish, poll every 10-15s
        time.sleep(APPCONFIG_WARMING_WAIT_TIME)

        new_appconfig_version_key = key_schema.appconfig_version_key(current_version + 1)
        new_appconfig_version_document = json.loads(redis_client.get(new_appconfig_version_key))
        latest_appconfig_key = key_schema.appconfig_latest_key()
        latest_appconfig_document = json.loads(redis_client.get(latest_appconfig_key))
        assert new_appconfig_version_document == latest_appconfig_document
