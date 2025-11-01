"""Helper utilities for AWS lambda functions.

Functions:
    base_url() -> str
        Extract correct public base URL from API Gateway event
    get_short_url() -> str
        Get string representation of short URL for a given shortcode

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

from typing import Dict, Any


def base_url(event: Dict[str, Any]) -> str:
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


def get_short_url(shortcode: str, event: Dict[str, Any]) -> str:
    """Get string representation of shortened URL
    
    Args:
        shortcode (str): shortcode 
        event (dict): API Gateway event object passed to Lambda handler

    Returns:
        str: short url string representation
    """
    return f'{base_url(event).rstrip("/")}/{shortcode}'
