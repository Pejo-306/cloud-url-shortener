import re

TEMPORARY_PASSWORD = '123456'

SHORTEN_ENDPOINT = '/v1/shorten'

CLOUDFORMATION_STACK_ARN_PATTERN = re.compile(
    r'^arn:(?P<partition>[^:]+):(?P<service>[^:]+):'
    r'(?P<region>[^:]+):(?P<account_id>[^:]+):'
    r'stack/(?P<stack_name>[^/]+)/(?P<stack_id>[^/]+)$'
)

APPCONFIG_WARMING_WAIT_TIME = 60  # seconds
