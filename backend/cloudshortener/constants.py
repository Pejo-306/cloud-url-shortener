from enum import StrEnum


class TTL:
    """TTL durations in seconds."""

    # Short URL TTL duration (data retention period) (1 year in seconds)
    ONE_YEAR = 31_536_000  # 60 * 60 * 24 * 365
    # Monthly user quota key TTL duration (1 month in seconds)
    ONE_MONTH = 2_592_000  # 60 * 60 * 24 * 30


class DefaultQuota:
    """Default quota values."""

    LINK_HITS = 10_000  # Default short URL monthly hit quota
    LINK_GENERATION = 20  # Default link generation quota for users


class ENV:
    """Environment variable names."""

    class App(StrEnum):
        APP_ENV = 'APP_ENV'
        APP_NAME = 'APP_NAME'
        PROJECT_ROOT = 'PROJECT_ROOT'
        AWS_SAM_LOCAL = 'AWS_SAM_LOCAL'
        LOG_LEVEL = 'LOG_LEVEL'

    class AppConfig(StrEnum):
        APP_ID = 'APPCONFIG_APP_ID'
        ENV_ID = 'APPCONFIG_ENV_ID'
        PROFILE_ID = 'APPCONFIG_PROFILE_ID'
        AGENT_URL = 'APPCONFIG_AGENT_URL'
        PROFILE_NAME = 'APPCONFIG_PROFILE_NAME'

    class ElastiCache(StrEnum):
        # SSM parameter paths for ElastiCache connection details
        HOST_PARAM = 'ELASTICACHE_HOST_PARAM'
        PORT_PARAM = 'ELASTICACHE_PORT_PARAM'
        DB_PARAM = 'ELASTICACHE_DB_PARAM'
        USER_PARAM = 'ELASTICACHE_USER_PARAM'
        # Secrets Manager name holding credentials JSON: {"username": "...", "password": "..."}
        SECRET = 'ELASTICACHE_SECRET'  # noqa: S105

    class LocalStack(StrEnum):
        ENDPOINT = 'LOCALSTACK_ENDPOINT'  # usually http://localstack:4566


# Error codes
UNKNOWN_INTERNAL_SERVER_ERROR = 'UNKNOWN_INTERNAL_SERVER_ERROR'
