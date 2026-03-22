import os

import pytest
import boto3
import redis

from cloudshortener.constants import ENV
from cloudshortener.utils.helpers import require_environment
from tests.integration.cloudformation import OrchestratorStack, Stacks
from tests.integration.data_stores import DataStores


@pytest.fixture(scope='session')
@require_environment(ENV.AWS.AWS_PROFILE)
def aws_session() -> boto3.Session:
    aws_profile = os.environ[ENV.AWS.AWS_PROFILE]
    return boto3.Session(profile_name=aws_profile)


@pytest.fixture(scope='session')
@require_environment(ENV.AWS.ORCHESTRATOR_STACK)
def stacks(aws_session: boto3.Session) -> Stacks:
    orchestrator_stack_name = os.environ[ENV.AWS.ORCHESTRATOR_STACK]
    orchestrator_stack = OrchestratorStack(name=orchestrator_stack_name, session=aws_session)
    stacks = {
        'OrchestratorStack': orchestrator_stack,
        **orchestrator_stack.nested_stacks,
    }
    return Stacks(stacks)


@pytest.fixture(scope='session')
def data_stores(stacks: Stacks) -> DataStores:
    appconfig = stacks.appconfig.get_latest_configuration()
    redis_config = appconfig['configs']['shorten_url']['redis']
    data_stores = {
        'redis': redis.Redis(**redis_config, decode_responses=True),
    }
    return DataStores(data_stores)
