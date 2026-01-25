import os
import random

from cloudshortener.utils.constants import APP_ENV_ENV, AWS_SAM_LOCAL_ENV


def running_locally() -> bool:
    """True if running in SAM local invoke/api, False otherwise"""
    env = os.getenv(APP_ENV_ENV, '').lower()
    return env == 'local' or os.getenv(AWS_SAM_LOCAL_ENV) == 'true'


def get_user_id(event: dict) -> str | None:
    claims = event.get('requestContext', {}).get('authorizer', {}).get('claims', {})
    user_id = claims.get('sub')

    # This is an ugly workaround to test lambdas locally with sam local api,
    # because we can't pass our own user id in the event.
    if user_id is None and running_locally():
        return f'lambda{random.randint(100, 999)}'  # noqa: S311
    return user_id
