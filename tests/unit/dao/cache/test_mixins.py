import json
from unittest.mock import MagicMock

import pytest
import redis
from botocore.client import BaseClient
from pytest import MonkeyPatch

from cloudshortener.dao.cache.mixins import ElastiCacheClientMixin
from cloudshortener.dao.cache.cache_key_schema import CacheKeySchema
from cloudshortener.utils.constants import ELASTICACHE_USER_PARAM_ENV


type SSMClient = BaseClient
type SecretsClient = BaseClient

class TestElastiCacheClientMixin:

    @pytest.fixture
    def ssm_client(self) -> SSMClient:
        client = MagicMock(spec=['get_parameter'])

        def _get_parameter(Name):  # noqa: N803
            if Name.endswith('/host'):
                return {'Parameter': {'Value': 'cache.internal'}}
            if Name.endswith('/port'):
                return {'Parameter': {'Value': '6380'}}
            if Name.endswith('/db'):
                return {'Parameter': {'Value': '5'}}
            if Name.endswith('/user'):
                return {'Parameter': {'Value': 'user_from_ssm'}}
            raise KeyError('Unknown parameter')

        client.get_parameter.side_effect = _get_parameter
        return client

    @pytest.fixture
    def secrets_client(self) -> SecretsClient:
        client = MagicMock(spec=['get_secret_value'])
        client.get_secret_value.return_value = {'SecretString': json.dumps({'username': 'user_from_secret', 'password': 'p'})}
        return client

    @pytest.fixture
    def secrets_client_without_username(self) -> SecretsClient:
        client = MagicMock(spec=['get_secret_value'])
        client.get_secret_value.return_value = {'SecretString': json.dumps({'password': 'p'})}
        return client

    @pytest.fixture(autouse=True)
    def setup(
        self,
        monkeypatch: MonkeyPatch,
        app_prefix: str,
        ssm_client: SSMClient,
        secrets_client: SecretsClient,
        secrets_client_without_username: SecretsClient,
        redis_client: redis.Redis,
    ) -> None:
        self.app_prefix = app_prefix
        self.ssm_client = ssm_client
        self.secrets_client = secrets_client
        self.secrets_client_without_username = secrets_client_without_username
        self.redis_client = redis_client

        # Make self.redis_client callable and return itself
        # So the internal mixin intialization records call args
        self.redis_client.return_value = redis_client
        monkeypatch.setattr('cloudshortener.dao.cache.mixins.redis.Redis', self.redis_client)

    def test_initialization_constructs_redis_and_keys(self):
        dao = ElastiCacheClientMixin(
            prefix=self.app_prefix,
            ssm_client=self.ssm_client,
            secrets_client=self.secrets_client,
            redis_decode_responses=True,
        )

        _, kwargs = self.redis_client.call_args
        assert kwargs['host'] == 'cache.internal'
        assert kwargs['port'] == 6380
        assert kwargs['db'] == 5
        assert kwargs['username'] == 'user_from_secret'
        assert kwargs['password'] == 'p'
        assert kwargs['decode_responses'] is True

        self.redis_client.ping.assert_called_once()

        assert isinstance(dao.keys, CacheKeySchema)
        assert dao.keys.prefix == f'cache:{self.app_prefix}'

        assert dao.redis is self.redis_client

    def test_secret_username_overrides_ssm_username(self):
        ElastiCacheClientMixin(
            prefix=self.app_prefix,
            ssm_client=self.ssm_client,
            secrets_client=self.secrets_client,
        )

        _, kwargs = self.redis_client.call_args
        assert kwargs['username'] == 'user_from_secret'
        assert kwargs['password'] == 'p'

    def test_fallback_to_ssm_username_when_secret_omits_username(self):
        ElastiCacheClientMixin(
            prefix=self.app_prefix,
            ssm_client=self.ssm_client,
            secrets_client=self.secrets_client_without_username,
        )

        _, kwargs = self.redis_client.call_args
        assert kwargs['username'] == 'user_from_ssm'
        assert kwargs['password'] == 'p'

    def test_username_none_when_no_secret_username_and_no_ssm_user_param(self, monkeypatch: MonkeyPatch):
        monkeypatch.delenv(ELASTICACHE_USER_PARAM_ENV, raising=False)

        ElastiCacheClientMixin(
            prefix=self.app_prefix,
            ssm_client=self.ssm_client,
            secrets_client=self.secrets_client_without_username,
        )

        _, kwargs = self.redis_client.call_args
        assert kwargs.get('username') is None
        assert kwargs['password'] == 'p'
