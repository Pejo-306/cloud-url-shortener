from botocore.client import BaseClient


type SSMClient = BaseClient
type SecretsClient = BaseClient
type CloudFormationClient = BaseClient
type AWSTag = dict[str, str]  # e.g. {"Key": "Owner", "Value": "Pesho"}
