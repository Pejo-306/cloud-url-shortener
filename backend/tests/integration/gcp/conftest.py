import os

import redis
import pytest

from cloudshortener.constants import ENV
from cloudshortener.utils.helpers import require_environment
from tests.integration.data_stores import DataStores
from tests.integration.gcp.components import GcpProject, Infrastructure
from tests.integration.gcp.constants import DEFAULT_REGION


@pytest.fixture(scope='session')
@require_environment(ENV.App.APP_NAME, ENV.App.APP_ENV, ENV.GCP.PROJECT_NUMBER, ENV.GCP.IDENTITY_WEB_API_KEY)
def project() -> GcpProject:
    app_name = os.environ[ENV.App.APP_NAME]
    app_env = os.environ[ENV.App.APP_ENV]
    project_id = os.environ.get(ENV.GCP.PROJECT_ID, f'{app_name}-{app_env}')
    project_number = os.environ[ENV.GCP.PROJECT_NUMBER]
    region = os.environ.get(ENV.GCP.REGION, DEFAULT_REGION)
    identity_web_api_key = os.environ[ENV.GCP.IDENTITY_WEB_API_KEY]
    # fmt: off
    return GcpProject(
        id=project_id,
        number=project_number,
        region=region,
        app_name=app_name,
        app_env=app_env,
        identity_web_api_key=identity_web_api_key
    )
    # fmt: on


@pytest.fixture(scope='session')
def infra(project: GcpProject) -> Infrastructure:
    return Infrastructure(project)


@pytest.fixture(scope='session')
def data_stores(infra: Infrastructure) -> DataStores:
    backend_config = infra.config.backend_config
    redis_config = backend_config['configs']['shorten_url']['redis']
    data_stores = {
        'redis': redis.Redis(**redis_config, decode_responses=True),
    }
    return DataStores(data_stores)
