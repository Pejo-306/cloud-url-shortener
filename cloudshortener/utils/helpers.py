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

        >>> event = {
        ...     "requestContext": {
        ...         "domainName": "localhost:3000",
        ...         "stage": "local"
        ...     }
        ... }
        >>> base_url(event)
        'http://localhost:3000'

        >>> base_url({})
        'http://localhost:3000'
"""

import os
import functools
import logging
import json
from datetime import datetime, UTC
from typing import Any
from collections.abc import Callable

from cloudshortener.utils.runtime import running_locally
from cloudshortener.utils.constants import UNKNOWN_INTERNAL_SERVER_ERROR


logger = logging.getLogger(__name__)


def base_url(event: dict[str, Any]) -> str:
    """Extract public base URL from API Gateway event

    Return the public base URL for the current Lambda invocation.

    Works seamlessly with custom domains, default AWS API Gateway domains,
    and local SAM domains. Custom domains omit stage names and use HTTPS.
    Default execute-api domains include the stage name. Local SAM domains
    use HTTP.

    Args:
        event (dict): API Gateway event object passed to Lambda handler

    Returns:
        str: Base URL, e.g.:
             - "https://petarnikolov.com"
             - "https://abc123.execute-api.us-east-1.amazonaws.com/Prod"
             - "http://localhost:3000"
    """
    request_context = event.get('requestContext', {})
    domain = request_context.get('domainName', '')
    stage = request_context.get('stage', '')

    if domain:
        if 'execute-api' in domain:
            # AWS default domains include the stage
            return f'https://{domain}/{stage}'

        # Custom domains use https; local SAM domains use http
        if domain.startswith(('localhost', '127.0.0.1')):
            return f'http://{domain}'
        return f'https://{domain}'

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


def guarantee_500_response(func: Callable) -> Callable:
    """Decorator: Guarantee a 500 HTTP response in case of unhandled exception

    NOTE: if the lambda is running locally, the exception is reraised. It's expected
          to be handled by a developer.

    Args:
        func (Callable): lambda handler

    Returns:
        Callable: decorated lambda handler with guaranteed 500 HTTP response

    Example:
        >>> @guarantee_500_response
        ... def lambda_handler(event, context):
        ...     raise Exception('test')
        >>> lambda_handler(event, context)
        {'statusCode': 500, 'body': '{"message": "Internal Server Error", "error_code": "UNKNOWN_INTERNAL_SERVER_ERROR"}'}
    """

    def _response_500() -> dict:
        body = {
            'message': 'Internal Server Error',
            'error_code': UNKNOWN_INTERNAL_SERVER_ERROR,
        }
        return {
            'statusCode': 500,
            'body': json.dumps(body),
        }

    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as error:
            extra = {'error': error.__class__.__name__, 'reason': str(error)}

            if running_locally():
                logger.exception('Unknown internal server error. Reraising exception.', extra=extra)
                raise error

            logger.exception('Unknown internal server error. Responding with 500.', extra=extra)
            return _response_500()

    return wrapper
