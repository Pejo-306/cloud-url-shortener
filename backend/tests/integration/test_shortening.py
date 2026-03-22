import uuid

import redis
import requests

from cloudshortener.utils.shortener import generate_shortcode, BASE
from cloudshortener.dao.exceptions import ShortURLNotFoundError
from cloudshortener.dao.redis import ShortURLRedisDAO
from tests.integration.cloudformation import Stacks
from tests.integration.data_stores import DataStores
from tests.integration.schemas import app_prefix


class TestShortening:
    def test_e2e_shortening(self, stacks: Stacks):
        # 0. Set target URL
        # 1. Authenticate with AWS Cognito
        # 2. Send a POST request to the shorten URL endpoint
        #   - Assert that the response is 200
        #   - Assert CORS headers are present
        # 3. Retrieve shortcode from response
        # 4. Send a GET request to the redirect URL endpoint
        #   - Assert that the response is 302
        #   - Assert CORS headers are present
        # 5. Assert that the redirect URL is the same as the original URL
        target_url = 'https://http.cat/405'

        with stacks.cognito.authenticate() as id_token:
            response = requests.post(
                url=stacks.backend.api.shorten_url,
                json={'targetUrl': target_url},
                headers={'Authorization': f'Bearer {id_token}'},
            )
            assert response.ok
            assert response.status_code == 200
            assert response.headers['Access-Control-Allow-Origin'] == '*'
            assert response.headers['Access-Control-Allow-Headers'] == 'Authorization,Content-Type'
            assert response.headers['Access-Control-Allow-Methods'] == 'OPTIONS,POST,GET'

            shortcode = response.json()['shortcode']
            response = requests.get(
                url=stacks.backend.api.redirect_url(shortcode),
                allow_redirects=False,
            )
            assert response.ok
            assert response.status_code == 302
            assert response.headers['Access-Control-Allow-Origin'] == '*'
            assert response.headers['Access-Control-Allow-Headers'] == 'Content-Type'
            assert response.headers['Access-Control-Allow-Methods'] == 'OPTIONS,POST,GET'
            assert response.headers['Location'] == target_url

    def test_unauthorized_shortening(self, stacks: Stacks):
        # 0. Set target URL
        # 1. Assert that we are not authenticated (just don't pass JWT token in requests)
        # 2. Send a POST request to the shorten URL endpoint
        # 3. Assert that the response is 401
        target_url = 'https://http.cat/405'
        response = requests.post(
            url=stacks.backend.api.shorten_url,
            json={'targetUrl': target_url},
        )
        assert response.status_code == 401

    def test_nonexistent_shortcode(self, stacks: Stacks, data_stores: DataStores):
        # 1. Generate a random shortcode
        # 2. Send a GET request to the redirect URL endpoint
        # 3. Assert that the response is 400
        key_prefix = app_prefix(stacks.orchestrator)
        shortcode = self._get_nonexistent_shortcode(redis_client=data_stores.redis, key_prefix=key_prefix)
        response = requests.get(
            url=stacks.backend.api.redirect_url(shortcode),
            allow_redirects=False,
        )
        assert response.status_code == 400  # TODO: shouldn't this respond with 404 instead?

    @staticmethod
    def _get_nonexistent_shortcode(
        redis_client: redis.Redis,
        key_prefix: str,
        length: int = 7,
        retries: int = 10,
    ) -> str:
        for _ in range(retries):
            salt = f'integration-tests-salt-{uuid.uuid4()}'
            shortcode = generate_shortcode(counter=BASE ^ length - 1, salt=salt)
            try:
                # TODO: short_url_dao should be a data-store-agnostic fixture
                short_url_dao = ShortURLRedisDAO(redis_client=redis_client, prefix=key_prefix)
                short_url_dao.get(shortcode)
            except ShortURLNotFoundError:
                return shortcode
        else:
            raise RuntimeError(
                f'Could not generate a unique non-existent shortcode after {retries} retries. '
                'Retry this test case or flush your backend data store.'
            )

    def test_non_conflict_shortening(self, stacks: Stacks):
        # 0. Set target URL
        # 1. Authenticate with AWS Cognito
        # 2. Send a POST request to the shorten URL endpoint
        # 3. Send a POST request to the shorten URL endpoint
        # 4. Assert that the shortcodes are different
        target_url = 'https://http.cat/405'

        with stacks.cognito.authenticate() as id_token:
            response1 = requests.post(
                url=stacks.backend.api.shorten_url,
                json={'targetUrl': target_url},
                headers={'Authorization': f'Bearer {id_token}'},
            )
            assert response1.ok
            assert response1.status_code == 200

            response2 = requests.post(
                url=stacks.backend.api.shorten_url,
                json={'targetUrl': target_url},
                headers={'Authorization': f'Bearer {id_token}'},
            )
            assert response2.ok
            assert response2.status_code == 200

            data1 = response1.json()
            data2 = response2.json()
            assert data1['shortcode'] != data2['shortcode']
