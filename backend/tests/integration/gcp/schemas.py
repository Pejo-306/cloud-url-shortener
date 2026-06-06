from cloudshortener.cloud.dao.cache import CacheKeySchema
from cloudshortener.dao.redis import RedisKeySchema
from tests.integration.gcp.components import GcpProject


def app_prefix(project: GcpProject) -> str:
    return f'{project.workload.app_name}:{project.workload.app_env}'


def redis_key_schema(project: GcpProject) -> RedisKeySchema:
    return RedisKeySchema(prefix=app_prefix(project))


def cache_key_schema(project: GcpProject) -> CacheKeySchema:
    return CacheKeySchema(prefix=app_prefix(project))
