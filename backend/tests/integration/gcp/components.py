import json
import os
import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass
from functools import cached_property

import redis
import requests
from google.cloud import apigateway_v1
from google.cloud import storage
from google.cloud import redis_v1
from google.cloud import secretmanager

from cloudshortener.constants import ENV
from cloudshortener.types import BackendConfig
from tests.integration.gcp.constants import (
    SHORTEN_ENDPOINT,
    CONFIG_OBJECT_NAME,
    TEMPORARY_PASSWORD,
    IDENTITY_TOOLKIT_SIGN_UP_PATH,
    IDENTITY_TOOLKIT_DELETE_USER_PATH,
)


class GcpProject:
    class Outputs:
        def __init__(self, app_name: str, app_env: str, identity_web_api_key: str):
            self._app_name = app_name
            self._app_env = app_env
            self._identity_web_api_key = identity_web_api_key

        @property
        def identity_web_api_key(self) -> str:
            return self._identity_web_api_key

        @property
        def memorystore_auth_secret_id(self) -> str:
            return f'{self._app_name}-{self._app_env}-secret-memorystore-auth'

    class Workload:
        class Outputs:
            def __init__(self, app_name: str, app_env: str, project_number: str):
                self._app_name = app_name
                self._app_env = app_env
                self._project_number = project_number

            @property
            def config_bucket_name(self) -> str:
                return f'{self._app_name}-{self._app_env}-config-{self._project_number}'

            @property
            def config_object_name(self) -> str:
                return CONFIG_OBJECT_NAME

        def __init__(self, app_name: str, app_env: str, project_number: str):
            self._app_name = app_name
            self._app_env = app_env
            self._outputs = self.Outputs(app_name, app_env, project_number)

        @property
        def app_name(self) -> str:
            return self._app_name

        @property
        def app_env(self) -> str:
            return self._app_env

        @property
        def outputs(self) -> Outputs:
            return self._outputs

    def __init__(self, id: str, number: str, region: str, app_name: str, app_env: str, identity_web_api_key: str):
        self._id = id
        self._number = number
        self._region = region
        self._outputs = self.Outputs(app_name, app_env, identity_web_api_key)
        self._workload = self.Workload(app_name, app_env, number)

    @property
    def id(self) -> str:
        return self._id

    @property
    def number(self) -> str:  # if number starts with '0', we can't represent it with an int
        return self._number

    @property
    def region(self) -> str:
        return self._region

    @property
    def outputs(self) -> Outputs:
        return self._outputs

    @property
    def workload(self) -> Workload:
        return self._workload


class InfrastructureComponent(ABC):
    def __init__(self, project: GcpProject):
        self._project = project
        self._name = None

    @property
    def project(self) -> GcpProject:
        return self._project

    @property
    def name(self) -> str:
        if self._name is None:
            self._name = f'{self.project.workload.app_name}-{self.project.workload.app_env}-{self._default_component_name}'
        return self._name

    @name.setter
    def name(self, name: str) -> None:
        self._name = name

    @property
    @abstractmethod
    def _default_component_name(self) -> str: ...


class ConfigurationComponent(InfrastructureComponent):
    def __init__(self, project: GcpProject):
        super().__init__(project)
        self._client = storage.Client(project=self.project.id)

    @cached_property
    def backend_config(self) -> BackendConfig:
        return self.read_backend_config()

    def read_backend_config(self) -> BackendConfig:
        bucket = self._client.bucket(self.project.workload.outputs.config_bucket_name)
        blob = bucket.blob(self.project.workload.outputs.config_object_name)
        raw = blob.download_as_text()
        config = json.loads(raw)
        return config

    def upload_new_backend_config_version(self) -> None:
        # Create a new configuration version from current deployed document with `build` bumped
        document = self.read_backend_config()
        document['build'] = int(document.get('build', 0)) + 1
        content = json.dumps(document).encode('utf-8')

        # Upload the new configuration version to GCS
        bucket = self._client.bucket(self.project.workload.outputs.config_bucket_name)
        blob = bucket.blob(self.project.workload.outputs.config_object_name)
        blob.upload_from_string(content, content_type='application/json')

    @property
    def _default_component_name(self) -> str:
        return 'config'


@dataclass(frozen=True)
class UserDetails:
    username: str
    email: str
    password: str
    id_token: str


class IdentityPlatformComponent(InfrastructureComponent):
    class Authenticator:
        def __init__(self, api_key: str):
            self._api_key = api_key
            self._user_details = None

        def __enter__(self) -> str:
            self._user_details = self._create_user()
            return self._user_details.id_token

        def __exit__(self, exc_type, exc_value, traceback) -> None:
            self._cleanup_existing_user()

        def _create_user(self) -> UserDetails:
            # NOTE: we assume UUID practically guarantees unique usernames
            username = f'integration-tests-user-{uuid.uuid4()}'
            email = f'{username}@example.com'
            password = TEMPORARY_PASSWORD
            response = requests.post(
                IDENTITY_TOOLKIT_SIGN_UP_PATH,
                params={'key': self._api_key},
                json={'email': email, 'password': password, 'returnSecureToken': True},
            )
            response.raise_for_status()

            data = response.json()
            id_token = data['idToken']
            user_details = UserDetails(username, email, password, id_token)
            return user_details

        def _cleanup_existing_user(self) -> None:
            if self._user_details is not None:
                try:
                    # fmt: off
                    response = requests.post(
                        IDENTITY_TOOLKIT_DELETE_USER_PATH,
                        params={'key': self._api_key},
                        json={'idToken': self._user_details.id_token}
                    )
                    # fmt: on
                    response.raise_for_status()
                except requests.exceptions.RequestException:
                    pass  # suppress exception if user was manually deleted in integration test
                finally:
                    self._user_details = None

    def authenticate(self) -> Authenticator:
        return self.Authenticator(api_key=self.project.outputs.identity_web_api_key)

    @property
    def _default_component_name(self) -> str:
        return 'identity-platform'


class BackendComponent(InfrastructureComponent):
    class BackendApi:
        def __init__(self, base_url: str, shorten_endpoint: str = SHORTEN_ENDPOINT):
            self._base_url = base_url.rstrip('/')
            self._shorten_endpoint = shorten_endpoint.lstrip('/')

        @property
        def shorten_url(self) -> str:
            return f'{self._base_url}/{self._shorten_endpoint}'

        def redirect_url(self, shortcode: str) -> str:
            return f'{self._base_url}/{shortcode.lstrip("/")}'

    def __init__(self, project: GcpProject):
        super().__init__(project)
        self._client = apigateway_v1.ApiGatewayServiceClient()

    @property
    def resource_path(self) -> str:
        return self._client.gateway_path(self.project.id, self.project.region, self.name)

    @cached_property
    def api(self) -> BackendApi:
        gateway = self._client.get_gateway(name=self.resource_path)
        base_url = f'https://{gateway.default_hostname}'
        api = self.BackendApi(base_url)
        return api

    @property
    def _default_component_name(self) -> str:
        return 'gw'


class MemoryStoreComponent(InfrastructureComponent):
    def __init__(self, project: GcpProject):
        super().__init__(project)
        self._client = redis_v1.CloudRedisClient()
        self._secrets_client = secretmanager.SecretManagerServiceClient()

    @property
    def resource_path(self) -> str:
        return self._client.instance_path(self.project.id, self.project.region, self.name)

    @cached_property
    def instance(self) -> redis_v1.Instance:
        return self._client.get_instance(name=self.resource_path)

    @property
    def host(self) -> str:
        local_host = os.environ.get(ENV.PortForwarding.HOST)
        return local_host or self.instance.host

    @property
    def port(self) -> int:
        local_port = os.environ.get(ENV.PortForwarding.PORT)
        return int(local_port or self.instance.port)

    @property
    def db(self) -> int:
        return 0  # we use the default database

    @property
    def username(self) -> None:
        return None  # we can't set a username for MemoryStore, so we let it use it's default

    @property
    def password(self) -> str:
        secret_name = self._secrets_client.secret_version_path(self.project.id, self.project.outputs.memorystore_auth_secret_id, 'latest')
        response = self._secrets_client.access_secret_version(name=secret_name)
        auth_string = response.payload.data.decode('utf-8')
        return auth_string

    @cached_property
    def redis(self) -> redis.Redis:
        # NOTE: we assume a port-forwarding google IAP session is established to the
        # bastion host, so we can access MemoryStore's Redis instance.
        redis_client = redis.Redis(
            host=self.host,
            port=self.port,
            db=self.db,
            username=self.username,
            password=self.password,
            ssl=True,
            ssl_cert_reqs='none',
            socket_connect_timeout=5.0,
            socket_timeout=5.0,
            decode_responses=True,
        )
        redis_client.ping()
        return redis_client

    @property
    def _default_component_name(self) -> str:
        return 'memorystore'


class Infrastructure:
    def __init__(self, project: GcpProject):
        self._identity_platform = IdentityPlatformComponent(project)
        self._config = ConfigurationComponent(project)
        self._backend = BackendComponent(project)
        self._memorystore = MemoryStoreComponent(project)

    @property
    def identity_platform(self) -> IdentityPlatformComponent:
        return self._identity_platform

    @property
    def config(self) -> ConfigurationComponent:
        return self._config

    @property
    def memorystore(self) -> MemoryStoreComponent:
        return self._memorystore

    @property
    def backend(self) -> BackendComponent:
        return self._backend
