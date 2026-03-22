from typing import TYPE_CHECKING, Any

from botocore.client import BaseClient


# Type aliases for Python dictionaries
type LambdaEvent = dict[str, Any]
type LambdaContext = Any
type LambdaResponse = dict[str, Any]
type LambdaDiagnosticResponse = str
type LambdaConfiguration = dict[str, Any]
type AppConfig = dict[str, Any]
type AppConfigMetadata = dict[str, Any]

# Type aliases for boto3 clients
type AppConfigDataClient = BaseClient
type AppConfigClient = BaseClient
type SSMClient = BaseClient
type SecretsClient = BaseClient

# TODO: all of the above boto3 types should be replaced with mypy_boto3_<service> types
if TYPE_CHECKING:
    from types_boto3_cloudformation.client import CloudFormationClient as CloudFormationClientStub
    from types_boto3_cognito_idp.client import CognitoIdentityProviderClient as CognitoIdpClientStub
    from types_boto3_elasticache.client import ElastiCacheClient as ElastiCacheClientStub

    type CloudFormationClient = CloudFormationClientStub
    type CognitoIdpClient = CognitoIdpClientStub
    type ElastiCacheClient = ElastiCacheClientStub
else:
    type CloudFormationClient = BaseClient
    type CognitoIdpClient = BaseClient
    type ElastiCacheClient = BaseClient

# Type aliases for HTTP objects
type HttpHeaders = dict[str, str]
