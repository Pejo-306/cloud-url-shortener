import requests

from cloudshortener.constants import DefaultQuota
from tests.integration.cloudformation import Stacks
from tests.integration.data_stores import DataStores
from tests.integration.schemas import redis_key_schema


class TestQuotaTracking:
    def test_user_creation_quota_tracking(self, stacks: Stacks):
        # 1. Authenticate with AWS Cognito
        # 2. Send a POST request to the shorten URL endpoint
        # 3. Assert user quota equals DEFAULT_QUOTA - 1
        # 4. Send a POST request to the shorten URL endpoint
        # 5. Assert user quota equals DEFAULT_QUOTA - 2
        target_url = 'https://http.cat/405'

        with stacks.cognito.authenticate() as id_token:
            response = requests.post(
                url=stacks.backend.api.shorten_url,
                json={'targetUrl': target_url},
                headers={'Authorization': f'Bearer {id_token}'},
            )
            remaining_quota = response.json()['remainingQuota']
            assert response.ok
            assert remaining_quota == DefaultQuota.LINK_GENERATION - 1

            response = requests.post(
                url=stacks.backend.api.shorten_url,
                json={'targetUrl': target_url},
                headers={'Authorization': f'Bearer {id_token}'},
            )
            remaining_quota = response.json()['remainingQuota']
            assert response.ok
            assert remaining_quota == DefaultQuota.LINK_GENERATION - 2

    def test_link_hit_quota_tracking(self, stacks: Stacks, data_stores: DataStores):
        # 0. Authenticate with AWS Cognito
        # 1. Send a POST request to the shorten URL endpoint
        # 2. Get the shortcode from the response
        # 3. Send a GET request to the redirect URL endpoint with the shortcode
        # 4. Assert link hit quota equals DEFAULT_QUOTA - 1
        # 5. Send a GET request to the redirect URL endpoint with the shortcode
        # 6. Assert link hit quota equals DEFAULT_QUOTA - 2
        target_url = 'https://http.cat/405'
        key_schema = redis_key_schema(stacks.orchestrator)

        with stacks.cognito.authenticate() as id_token:
            response = requests.post(
                url=stacks.backend.api.shorten_url,
                json={'targetUrl': target_url},
                headers={'Authorization': f'Bearer {id_token}'},
            )
            shortcode = response.json()['shortcode']
            short_url = stacks.backend.api.redirect_url(shortcode)

        link_hits_key = key_schema.link_hits_key(shortcode)
        remaining_link_hits = int(data_stores.redis.get(link_hits_key))
        assert remaining_link_hits == DefaultQuota.LINK_HITS

        response = requests.get(url=short_url, allow_redirects=False)
        remaining_link_hits = int(data_stores.redis.get(link_hits_key))
        assert response.ok
        assert remaining_link_hits == DefaultQuota.LINK_HITS - 1

        response = requests.get(url=short_url, allow_redirects=False)
        remaining_link_hits = int(data_stores.redis.get(link_hits_key))
        assert response.ok
        assert remaining_link_hits == DefaultQuota.LINK_HITS - 2
