"""Unit tests for helper functions in helpers.py.

Test coverage includes:

1. base_url() correct extraction
   - 1.1. Ensures URLs include the stage (e.g., `/Prod`) when invoked via AWS.
   - 1.2. Ensures URLs do NOT include stage information for clean public links.
   - 1.3. Confirms a proper localhost fallback is returned when no domain is present.
   - 1.4. Ensures graceful fallback behavior when API Gateway data is partially missing.
"""

import pytest

from cloudshortener.utils.helpers import base_url


# -------------------------------
# 1.1. AWS default domain handling
# -------------------------------

@pytest.mark.parametrize(
    'domain, stage, expected', [
        ('abc123.execute-api.us-east-1.amazonaws.com', 'Dev', 'https://abc123.execute-api.us-east-1.amazonaws.com/Dev'),
        ('xyz789.execute-api.us-east-1.amazonaws.com', 'Dev', 'https://xyz789.execute-api.us-east-1.amazonaws.com/Dev'),
        ('abc123.execute-api.us-east-1.amazonaws.com', 'Prod', 'https://abc123.execute-api.us-east-1.amazonaws.com/Prod'),
    ]
)
def test_base_url_with_aws_domain(domain, stage, expected):
    """Ensure base_url() appends stage for default AWS execute-api domains."""
    event = {
        'requestContext': {
            'domainName': domain,
            'stage': stage,
        }
    }
    result = base_url(event)
    assert result == expected


# -------------------------------
# 1.2. Custom domain handling
# -------------------------------

@pytest.mark.parametrize(
    'domain, stage, expected', [
        ('lambda.hello.com', 'Dev', 'https://lambda.hello.com'),
        ('example.com', 'Prod', 'https://example.com'),
    ]
)
def test_base_url_with_custom_domain(domain, stage, expected):
    """Ensure base_url() excludes stage for custom user-defined domains."""
    event = {
        'requestContext': {
            'domainName': domain,
            'stage': stage,
        }
    }
    result = base_url(event)
    assert result == expected


# -------------------------------
# 1.3. Local fallback behavior
# -------------------------------

def test_base_url_local_fallback():
    """Ensure base_url() returns localhost URL when no domain is provided."""
    event = {}
    result = base_url(event)
    assert result == 'http://localhost:3000'


# -------------------------------
# 1.4. Missing or partial requestContext
# -------------------------------

@pytest.mark.parametrize('event', [
    {'requestContext': {}},
    {'requestContext': {'domainName': ''}},
    {'requestContext': {'stage': 'Dev'}},
])
def test_base_url_handles_incomplete_context(event):
    """Ensure base_url() gracefully falls back when requestContext is incomplete."""
    result = base_url(event)
    assert result == "http://localhost:3000"
