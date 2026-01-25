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


def base_url(event: dict[str, Any]) -> str:  # TODO: transform dict[str, Any] to custom type
    """Return the public base URL for the current Lambda event.

    Examples:
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
    """String representation of the shortened URL for a given shortcode."""
    return f'{base_url(event).rstrip("/")}/{shortcode}'


def beginning_of_next_month() -> datetime:
    now = datetime.now(UTC)
    next_month = (now.month % 12) + 1
    next_year = now.year + (1 if now.month == 12 else 0)
    return datetime(next_year, next_month, 1, 0, 0, 0, tzinfo=UTC)


def require_environment(*names: str) -> Callable:
    """Decorator: Ensure required environment variables are present before executing the callable."""

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            missing = [name for name in names if not os.environ.get(name)]
            if missing:
                missing_list = ', '.join(f"'{name}'" for name in missing)
                raise KeyError(f'Missing required environment variables: {missing_list}')  # TODO: use custom exception
            return func(*args, **kwargs)

        return wrapper

    return decorator


def guarantee_500_response(lambda_handler: Callable) -> Callable:
    """Decorator: Guarantee a 500 HTTP response in case of unhandled exception

    NOTE: if the lambda is running locally, the exception is reraised. It's expected
          to be handled by a developer.
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

    @functools.wraps(lambda_handler)
    def wrapper(*args, **kwargs):
        try:
            return lambda_handler(*args, **kwargs)
        except Exception as error:
            extra = {'error': error.__class__.__name__, 'reason': str(error)}

            if running_locally():
                logger.exception('Unknown internal server error. Reraising exception.', extra=extra)
                raise error

            logger.exception('Unknown internal server error. Responding with 500.', extra=extra)
            return _response_500()

    return wrapper
