import os
import random

from cloudshortener.types import LambdaEvent
from cloudshortener.constants import ENV


def running_locally() -> bool:
    """Return True if running in SAM local invoke/api, False otherwise."""
    env = os.getenv(ENV.App.APP_ENV, '').lower()
    return env == 'local' or os.getenv(ENV.App.AWS_SAM_LOCAL) == 'true'


def get_user_id(event: LambdaEvent) -> str | None:
    claims = event.get('requestContext', {}).get('authorizer', {}).get('claims', {})
    user_id = claims.get('sub')

    # This is an ugly workaround to test lambdas locally with sam local api,
    # because we can't pass our own user id in the event.
    if user_id is None and running_locally():
        return f'lambda{random.randint(100, 999)}'  # noqa: S311
    return user_id
