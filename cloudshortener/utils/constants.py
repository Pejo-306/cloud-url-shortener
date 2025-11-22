# Default short URL TTL duration
ONE_YEAR_SECONDS = 31_536_000  # 60 * 60 * 24 * 365
ONE_MONTH_SECONDS = 2_592_000  # 60 * 60 * 24 * 30

# Default short URL monthly hit quota
DEFAULT_LINK_HITS_QUOTA = 10_000

# Default link generation quota for users
DEFAULT_LINK_GENERATION_QUOTA = 20

# ElastiCache: SSM parameter paths for ElastiCache connection details
ELASTICACHE_HOST_PARAM_ENV = 'ELASTICACHE_HOST_PARAM'
ELASTICACHE_PORT_PARAM_ENV = 'ELASTICACHE_PORT_PARAM'
ELASTICACHE_DB_PARAM_ENV = 'ELASTICACHE_DB_PARAM'
ELASTICACHE_USER_PARAM_ENV = 'ELASTICACHE_USER_PARAM'  # optional

# ElastiCache: Secrets Manager name holding credentials JSON: {"username": "...", "password": "..."}
ELASTICACHE_SECRET_ENV = 'ELASTICACHE_SECRET'

# LocalStack: endpoint URL environment variable for local development
LOCALSTACK_ENDPOINT_ENV = 'LOCALSTACK_ENDPOINT'
