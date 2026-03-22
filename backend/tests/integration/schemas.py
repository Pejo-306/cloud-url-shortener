from cloudshortener.dao.redis import RedisKeySchema
from cloudshortener.dao.cache import CacheKeySchema
from tests.integration.cloudformation import CloudFormationStack


def app_prefix(stack: CloudFormationStack) -> str:
    return f'{stack.app_name}:{stack.app_env}'


def redis_key_schema(stack: CloudFormationStack) -> RedisKeySchema:
    return RedisKeySchema(prefix=app_prefix(stack))


def cache_key_schema(stack: CloudFormationStack) -> CacheKeySchema:
    return CacheKeySchema(prefix=app_prefix(stack))
