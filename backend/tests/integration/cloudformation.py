import os
import base64
import json
import uuid
from datetime import datetime
from dataclasses import dataclass
from typing import NotRequired, Optional, TypedDict, cast
from functools import cached_property

import boto3
import redis

from cloudshortener.types import (
    CloudFormationClient,
    CognitoIdpClient,
    AppConfig,
    AppConfigDataClient,
    AppConfigClient,
    SSMClient,
    SecretsClient,
    ElastiCacheClient,
)
from cloudshortener.constants import ENV, SSMParameterPaths, SecretsManagerNames
from tests.integration.constants import TEMPORARY_PASSWORD, SHORTEN_ENDPOINT, CLOUDFORMATION_STACK_ARN_PATTERN


type LogicalResourceId = str
type OutputKey = str
type ParameterKey = str


class StackOutput(TypedDict):
    OutputKey: OutputKey
    OutputValue: str
    Description: NotRequired[str]
    ExportName: NotRequired[str]


class StackResourceDriftInformation(TypedDict):
    StackResourceDriftStatus: NotRequired[str]
    LastCheckTimestamp: NotRequired[datetime]


class StackResourceModuleInfo(TypedDict):
    TypeHierarchy: NotRequired[str]
    LogicalIdHierarchy: NotRequired[str]


class StackResource(TypedDict):
    LogicalResourceId: LogicalResourceId
    ResourceType: str
    ResourceStatus: str
    StackId: str
    StackName: str
    Timestamp: datetime
    PhysicalResourceId: NotRequired[str]
    ResourceStatusReason: NotRequired[str]
    Description: NotRequired[str]
    DriftInformation: NotRequired[StackResourceDriftInformation]
    ModuleInfo: NotRequired[StackResourceModuleInfo]


class StackParameter(TypedDict):
    ParameterKey: ParameterKey
    ParameterValue: str
    UsePreviousValue: NotRequired[bool]
    ResolvedValue: NotRequired[str]


class CloudFormationStack:
    def __init__(self, name: str, session: Optional[boto3.Session] = None):
        self._name = name
        self._session = session or boto3.Session()
        self._cloudformation_client = self._session.client('cloudformation')
        self._ssm_client = self._session.client('ssm')
        self._secrets_client = self._session.client('secretsmanager')

    @property
    def name(self) -> str:
        return self._name

    @property
    def app_name(self) -> str:
        return self.parameters['AppName']['ParameterValue']

    @property
    def app_env(self) -> str:
        return self.parameters['AppEnv']['ParameterValue']

    @property
    def session(self) -> boto3.Session:
        return self._session

    @property
    def cloudformation_client(self) -> CloudFormationClient:
        return self._cloudformation_client

    @property
    def ssm_client(self) -> SSMClient:
        return self._ssm_client

    @property
    def secrets_client(self) -> SecretsClient:
        return self._secrets_client

    @cached_property
    def outputs(self) -> dict[OutputKey, StackOutput]:
        raw_outputs = self._cloudformation_client.describe_stacks(StackName=self.name)['Stacks'][0]['Outputs']
        return {output['OutputKey']: output for output in raw_outputs}

    @cached_property
    def resources(self) -> dict[LogicalResourceId, StackResource]:
        raw_resources = self._cloudformation_client.describe_stack_resources(StackName=self.name)['StackResources']
        return {resource['LogicalResourceId']: resource for resource in raw_resources}

    @cached_property
    def parameters(self) -> dict[ParameterKey, StackParameter]:
        raw_parameters = self._cloudformation_client.describe_stacks(StackName=self.name)['Stacks'][0]['Parameters']
        return {parameter['ParameterKey']: parameter for parameter in raw_parameters}


class AppConfigStack(CloudFormationStack):
    def __init__(self, name: str, session: Optional[boto3.Session] = None):
        super().__init__(name, session)
        self._appconfig_data_client = self.session.client('appconfigdata')
        self._appconfig_client = self.session.client('appconfig')
        self._application_id = self.outputs['AppConfigApplicationId']['OutputValue']
        self._environment_id = self.outputs['AppConfigEnvironmentId']['OutputValue']
        self._profile_id = self.outputs['BackendConfigProfileId']['OutputValue']
        self._strategy_id = self.resources['AppConfigFastDeploymentStrategy']['PhysicalResourceId']

    @property
    def data_client(self) -> AppConfigDataClient:
        return self._appconfig_data_client

    @property
    def client(self) -> AppConfigClient:
        return self._appconfig_client

    def get_latest_configuration(self) -> AppConfig:
        token = self._appconfig_data_client.start_configuration_session(
            ApplicationIdentifier=self._application_id,
            EnvironmentIdentifier=self._environment_id,
            ConfigurationProfileIdentifier=self._profile_id,
        )['InitialConfigurationToken']
        response = self._appconfig_data_client.get_latest_configuration(ConfigurationToken=token)

        body = response['Configuration']
        content = body.read() if hasattr(body, 'read') else body
        return json.loads((content or b'').decode('utf-8'))

    def deploy_new_hosted_configuration_version(self, wait: bool = True) -> Optional[AppConfig]:
        # Create a new configuration version from current deployed document with `build` bumped
        document = self.get_latest_configuration()
        document['build'] = int(document.get('build', 0)) + 1
        content = json.dumps(document).encode('utf-8')
        creation_response = self._appconfig_client.create_hosted_configuration_version(
            ApplicationId=self._application_id,
            ConfigurationProfileId=self._profile_id,
            Content=content,
            ContentType='application/json',
            Description='integration-test',
        )
        version = int(creation_response['VersionNumber'])

        # Deploy the new configuration version
        deployment_response = self._appconfig_client.start_deployment(
            ApplicationId=self._application_id,
            EnvironmentId=self._environment_id,
            ConfigurationProfileId=self._profile_id,
            ConfigurationVersion=str(version),
            DeploymentStrategyId=self._strategy_id,
            Description=f'Integration test deployment version {version}',
        )

        # Wait for the deployment to complete
        if wait:
            deployment_number = deployment_response['DeploymentNumber']
            waiter = self._appconfig_client.get_waiter('deployment_complete')
            waiter.wait(
                ApplicationId=self._application_id,
                EnvironmentId=self._environment_id,
                DeploymentNumber=deployment_number,
                WaiterConfig={'Delay': 5, 'MaxAttempts': 60},
            )
            return self.get_latest_configuration()


@dataclass(frozen=True)
class UserDetails:
    username: str
    email: str
    password: str
    user_id: str  # Cognito JWT `sub` claim


class CognitoStack(CloudFormationStack):
    class Authenticator:
        def __init__(self, client: CognitoIdpClient, user_pool_id: str, user_pool_client_id: str):
            self._client = client
            self._user_pool_id = user_pool_id
            self._user_pool_client_id = user_pool_client_id
            self._user_details = None

        def __enter__(self) -> str:
            username, email, password = self._create_user()
            response = self._client.initiate_auth(
                AuthFlow='USER_PASSWORD_AUTH',
                ClientId=self._user_pool_client_id,
                AuthParameters={
                    'USERNAME': username,
                    'PASSWORD': password,
                },
            )
            if 'AuthenticationResult' not in response:
                raise ValueError(f'Failed to authenticate user {username}: {response}')

            id_token = response['AuthenticationResult']['IdToken']
            user_id = self.__extract_sub_claim(id_token)
            self._user_details = UserDetails(username, email, password, user_id)
            return id_token

        def __exit__(self, exc_type, exc_value, traceback) -> None:
            # Teardown: delete test user if one was created via authenticate()
            self._cleanup_existing_user()

        def _create_user(self) -> tuple[str, str, str]:
            # NOTE: we assume UUID practically guarantees unique usernames
            username = f'integration-tests-user-{uuid.uuid4()}'
            email = f'{username}@example.com'
            password = TEMPORARY_PASSWORD
            self._client.admin_create_user(
                UserPoolId=self._user_pool_id,
                Username=username,
                UserAttributes=[
                    {'Name': 'email', 'Value': email},
                    {'Name': 'email_verified', 'Value': 'true'},
                ],
                MessageAction='SUPPRESS',  # don't send any confirmation emails to the user
                TemporaryPassword=TEMPORARY_PASSWORD,
            )

            # Unstuck user from `FORCE_CHANGE_PASSWORD` status
            self._client.admin_set_user_password(
                UserPoolId=self._user_pool_id,
                Username=username,
                Password=password,
                Permanent=True,
            )
            return username, email, password

        def _cleanup_existing_user(self) -> None:
            if self._user_details is not None:
                try:
                    self._client.admin_delete_user(
                        UserPoolId=self._user_pool_id,
                        Username=self._user_details.username,
                    )
                except self._client.exceptions.UserNotFoundException:
                    pass  # suppress exception if user was manually deleted in integration test
                finally:
                    self._user_details = None

        @staticmethod
        def __extract_sub_claim(id_token: str) -> str:
            # vibecoded with composer-2-fast, don't ask me how this works
            # TL;DR: the sub is embedded in the ID token and we extract it in this function
            parts = id_token.split('.')
            if len(parts) != 3:
                raise ValueError('ID token must have three dot-separated segments')
            payload_b64 = parts[1]
            rem = len(payload_b64) % 4
            if rem:
                payload_b64 += '=' * (4 - rem)
            try:
                raw = base64.urlsafe_b64decode(payload_b64)
                payload = json.loads(raw)
            except (json.JSONDecodeError, UnicodeDecodeError) as e:
                raise ValueError('ID token payload is not valid JSON') from e
            sub = payload.get('sub')
            if not isinstance(sub, str) or not sub:
                raise ValueError("ID token payload missing non-empty 'sub' claim")
            return sub

    def __init__(self, name: str, session: Optional[boto3.Session] = None):
        super().__init__(name, session)
        self._client = self.session.client('cognito-idp')
        self._user_pool_id = self.outputs['UserPoolId']['OutputValue']
        self._user_pool_client_id = self.outputs['UserPoolClientId']['OutputValue']
        self._authenticator = None

    @property
    def client(self) -> CognitoIdpClient:
        return self._client

    @property
    def user_details(self) -> UserDetails:
        if self._authenticator is None:
            raise RuntimeError('User details not set; call authenticate() first')
        if self._authenticator._user_details is None:
            self._authenticator = None
            raise RuntimeError('User details not set; call authenticate() first')
        return self._authenticator._user_details

    def authenticate(self) -> Authenticator:
        self._authenticator = self.Authenticator(
            client=self._client, user_pool_id=self._user_pool_id, user_pool_client_id=self._user_pool_client_id
        )
        return self._authenticator


class BackendStack(CloudFormationStack):
    class BackendApi:
        def __init__(self, base_url: str, shorten_endpoint: str = SHORTEN_ENDPOINT):
            self._base_url = base_url.rstrip('/')
            self._shorten_endpoint = shorten_endpoint.lstrip('/')

        @property
        def shorten_url(self) -> str:
            return f'{self._base_url}/{self._shorten_endpoint}'

        def redirect_url(self, shortcode: str) -> str:
            return f'{self._base_url}/{shortcode.lstrip("/")}'

    def __init__(self, name: str, session: Optional[boto3.Session] = None):
        super().__init__(name, session)
        base_url = self.outputs['ApiUrl']['OutputValue']
        self._api = self.BackendApi(base_url)

    @property
    def api(self) -> BackendApi:
        return self._api


class ElastiCacheStack(CloudFormationStack):
    def __init__(self, name: str, session: Optional[boto3.Session] = None):
        super().__init__(name, session)
        self._client = self.session.client('elasticache')
        self._redis_client = None

    @property
    def client(self) -> ElastiCacheClient:
        return self._client

    @cached_property
    def host(self) -> str:
        local_host = os.environ.get(ENV.PortForwarding.HOST)
        host_param = SSMParameterPaths.ElastiCache.HOST.format(app_name=self.app_name, app_env=self.app_env)
        return local_host or self._ssm_client.get_parameter(Name=host_param)['Parameter']['Value']

    @cached_property
    def port(self) -> int:
        local_port = os.environ.get(ENV.PortForwarding.PORT)
        port_param = SSMParameterPaths.ElastiCache.PORT.format(app_name=self.app_name, app_env=self.app_env)
        return int(local_port or self._ssm_client.get_parameter(Name=port_param)['Parameter']['Value'])

    @cached_property
    def db(self) -> int:
        db_param = SSMParameterPaths.ElastiCache.DB.format(app_name=self.app_name, app_env=self.app_env)
        return int(self._ssm_client.get_parameter(Name=db_param)['Parameter']['Value'])

    @cached_property
    def username(self) -> str:
        secret_name = SecretsManagerNames.ElastiCache.CREDENTIALS.format(app_name=self.app_name, app_env=self.app_env)
        raw_secret = self._secrets_client.get_secret_value(SecretId=secret_name)['SecretString']
        credentials = json.loads(raw_secret)
        return credentials['username']

    @cached_property
    def password(self) -> str:
        secret_name = SecretsManagerNames.ElastiCache.CREDENTIALS.format(app_name=self.app_name, app_env=self.app_env)
        raw_secret = self._secrets_client.get_secret_value(SecretId=secret_name)['SecretString']
        credentials = json.loads(raw_secret)
        return credentials['password']

    @cached_property
    def redis(self) -> redis.Redis:
        # NOTE: we assume a port-forwarding SSM session is established to the
        # bastion host, so we can access ElastiCache's Redis instance.
        redis_client = redis.Redis(
            host=self.host,
            port=self.port,
            db=self.db,
            username=self.username,
            password=self.password,
            ssl=True,
            ssl_cert_reqs=None,
            socket_connect_timeout=5.0,
            socket_timeout=5.0,
            decode_responses=True,
        )
        redis_client.ping()
        return redis_client


NESTED_STACKS_LOGICAL_IDS_TO_CLASSES = {
    'CognitoStack': CognitoStack,
    'AppConfigStack': AppConfigStack,
    'ElastiCacheStack': ElastiCacheStack,
    'BackendStack': BackendStack,
}


class OrchestratorStack(CloudFormationStack):
    @cached_property
    def nested_stacks(self) -> dict[LogicalResourceId, CloudFormationStack]:
        logical_ids = NESTED_STACKS_LOGICAL_IDS_TO_CLASSES.keys()
        # fmt: off
        stack_arns = {
            logical_id: self.resources[logical_id]['PhysicalResourceId']
            for logical_id in logical_ids
        }
        stack_names = {
            logical_id: CLOUDFORMATION_STACK_ARN_PATTERN.match(arn).group('stack_name')
            for logical_id, arn in stack_arns.items()
        }
        stacks = {
            logical_id: NESTED_STACKS_LOGICAL_IDS_TO_CLASSES[logical_id](name=stack_names[logical_id], session=self.session)
            for logical_id in logical_ids
        }
        # fmt: on
        # Output looks like:
        # {
        #     'CognitoStack': CognitoStack(
        #         name='cloudshortener-dev-CognitoStack-1234567890',
        #         session=self.session,
        #     ),
        #     'AppConfigStack': AppConfigStack(
        #         name='cloudshortener-dev-AppConfigStack-1234567890',
        #         session=self.session,
        #     ),
        #     'ElastiCacheStack': ElastiCacheStack(
        #         name='cloudshortener-dev-ElastiCacheStack-1234567890',
        #         session=self.session,
        #     ),
        #     'BackendStack': BackendStack(
        #         name='cloudshortener-dev-BackendStack-1234567890',
        #         session=self.session,
        #     ),
        # }
        return stacks


class Stacks:
    def __init__(self, stacks: dict[LogicalResourceId, CloudFormationStack]):
        self._orchestrator = cast(OrchestratorStack, stacks['OrchestratorStack'])
        self._cognito = cast(CognitoStack, stacks['CognitoStack'])
        self._appconfig = cast(AppConfigStack, stacks['AppConfigStack'])
        self._elasticache = cast(ElastiCacheStack, stacks['ElastiCacheStack'])
        self._backend = cast(BackendStack, stacks['BackendStack'])

    @property
    def orchestrator(self) -> OrchestratorStack:
        return self._orchestrator

    @property
    def cognito(self) -> CognitoStack:
        return self._cognito

    @property
    def appconfig(self) -> AppConfigStack:
        return self._appconfig

    @property
    def elasticache(self) -> ElastiCacheStack:
        return self._elasticache

    @property
    def backend(self) -> BackendStack:
        return self._backend
