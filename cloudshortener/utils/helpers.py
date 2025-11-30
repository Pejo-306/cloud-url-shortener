"""Helper utilities for AWS lambda functions.

Functions:
    base_url() -> str
        Extract correct public base URL from API Gateway event
    get_short_url() -> str
        Get string representation of short URL for a given shortcode
    beginning_of_next_month() -> datetime
        Compute the first moment of the next calendar month in UTC
    require_environment(*names: str) -> Callable
        Decorator: Ensure required environment variables are present

Example:
    Typical usage inside a Lambda handler:

        >>> from cloudshortener.utils.helpers import base_url
        >>> event = {
        ...     "requestContext": {
        ...         "domainName": "abc123.execute-api.us-east-1.amazonaws.com",
        ...         "stage": "Prod"
        ...     }
        ... }
        >>> base_url(event)
        'https://abc123.execute-api.us-east-1.amazonaws.com/Prod'

        >>> event = {
        ...     "requestContext": {
        ...         "domainName": "petarnikolov.com",
        ...         "stage": "Prod"
        ...     }
        ... }
        >>> base_url(event)
        'https://petarnikolov.com'

        >>> base_url({})
        'http://localhost:3000'
"""

import os
import functools
from datetime import datetime, UTC
from typing import Any
from collections.abc import Callable


def base_url(event: dict[str, Any]) -> str:
    """Extract public base URL from API Gateway event

    Return the public base URL for the current Lambda invocation.

    Works seamlessly with both custom and default AWS API Gateway domains.
    If a custom domain is configured, the stage name is omitted.
    If using the default AWS execute-api domain, the stage name is included.

    Args:
        event (dict): API Gateway event object passed to Lambda handler

    Returns:
        str: Base URL, e.g.:
             - "https://petarnikolov.com"
             - "https://abc123.execute-api.us-east-1.amazonaws.com/Prod"
    """
    request_context = event.get('requestContext', {})
    domain = request_context.get('domainName', '')
    stage = request_context.get('stage', '')

    if domain and 'execute-api' not in domain:
        # If the domain is a custom domain (no execute-api), skip stage
        return f'https://{domain}'
    elif domain:
        # Otherwise include the stage (for AWS default domains)
        return f'https://{domain}/{stage}'
    else:
        # Fallback: local invocation (SAM CLI, tests, etc.)
        return 'http://localhost:3000'


def get_short_url(shortcode: str, event: dict[str, Any]) -> str:
    """Get string representation of shortened URL

    Args:
        shortcode (str): shortcode
        event (dict): API Gateway event object passed to Lambda handler

    Returns:
        str: short url string representation
    """
    return f'{base_url(event).rstrip("/")}/{shortcode}'


def beginning_of_next_month() -> datetime:
    """Compute the first moment of the next calendar month in UTC.

    Returns:
        datetime:
            Newly constructed datetime value representing the very start
            (00:00:00) of the next calendar month in UTC.

    Example:
        >>> beginning_of_next_month()
        datetime.datetime(2025, 11, 1, 0, 0, 0, tzinfo=datetime.timezone.utc)
    """
    now = datetime.now(UTC)
    next_month = (now.month % 12) + 1
    next_year = now.year + (1 if now.month == 12 else 0)

    return datetime(next_year, next_month, 1, 0, 0, 0, tzinfo=UTC)


def require_environment(*names: str) -> Callable:
    """Decorator ensuring required environment variables are present.

    Args:
        *names (str):
            Names of required environment variables.

    Raises:
        ValueError:
            If any required environment variable is missing or empty.

    Example:
        >>> @require_environment('AWS_ACCESS_KEY_ID', 'AWS_SECRET_ACCESS_KEY')
        ... def my_function():
        ...     pass
        >>> my_function()
        ValueError: Missing required environment variables: 'AWS_ACCESS_KEY_ID', 'AWS_SECRET_ACCESS_KEY'
    """

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            missing = [name for name in names if not os.environ.get(name)]
            if missing:
                missing_list = ', '.join(f"'{name}'" for name in missing)
                raise KeyError(f'Missing required environment variables: {missing_list}')
            return func(*args, **kwargs)

        return wrapper

    return decorator
