"""Runtime utilities

Functions:
    running_locally() -> bool:
        True if lambda is running in local SAM, False otherwise.
    get_user_id(event: dict) -> str | None:
        Get the user id from the event.
        If the lambda is running locally, return a random user id.
        If the lambda is running in a real environment, return the user id from the event.

Example:
    >>> fromt cloudshortener.utils.runtime import running_locally
    >>> os.environ['APP_ENV'] = 'local'
    >>> running_locally()
    True
    >>> os.environ['APP_ENV'] = 'dev'
    >>> running_locally()
    False
"""

import os
import random

from cloudshortener.utils.constants import APP_ENV_ENV, AWS_SAM_LOCAL_ENV


def running_locally() -> bool:
    """Check if the lambda is running locally via sam local invoke

    Returns:
        bool: True if running locally, False otherwise.

    Example:
        >>> os.environ['APP_ENV'] = 'local'
        >>> running_locally()
        True
        >>> os.environ['APP_ENV'] = 'dev'
        >>> running_locally()
        False
    """
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
