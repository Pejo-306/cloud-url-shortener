from typing import Any

from botocore.client import BaseClient


# Type aliases for Python dictionaries
type LambdaEvent = dict[str, Any]
type LambdaContext = Any
type LambdaResponse = dict[str, Any]
type LambdaConfiguration = dict[str, Any]
type AppConfig = dict[str, Any]
type AppConfigMetadata = dict[str, Any]

# Type aliases for boto3 clients
type AppConfigDataClient = BaseClient
type AppConfigClient = BaseClient
