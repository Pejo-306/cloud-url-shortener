"""Runtime utilities

Functions:
    running_locally() -> bool:
        True if lambda is running in local SAM, False otherwise.

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
