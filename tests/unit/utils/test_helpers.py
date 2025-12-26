"""Unit tests for helper functions in helpers.py.

Test coverage includes:

1. base_url() correct extraction
   - 1.1. Ensures URLs include the stage (e.g., `/Prod`) when invoked via AWS.
   - 1.2. Ensures URLs do NOT include stage information for clean public links.
   - 1.3. Confirms a proper localhost fallback is returned when no domain is present.
   - 1.4. Ensures graceful fallback behavior when API Gateway data is partially missing.

2. get_short_url() retrieves short URL string representation

3. beginning_of_next_month() computes next month's first moment
   - 3.1. Ensures correct calculation for various dates throughout the year.
   - 3.2. Validates year rollover behavior at December boundaries.

4. require_environment() decorator behavior
   - 4.1. Ensures decorated functions execute when all env vars are present.
   - 4.2. Ensures missing or empty env vars raise a descriptive ValueError.
"""

import json
from datetime import datetime, UTC

import pytest
from freezegun import freeze_time

from cloudshortener.utils.helpers import (
    base_url,
    get_short_url,
    beginning_of_next_month,
    require_environment,
    guarantee_500_response,
)


# -------------------------------
# 1.1. AWS default domain handling
# -------------------------------


@pytest.mark.parametrize(
    'domain, stage, expected',
    [
        ('abc123.execute-api.us-east-1.amazonaws.com', 'Dev', 'https://abc123.execute-api.us-east-1.amazonaws.com/Dev'),
        ('xyz789.execute-api.us-east-1.amazonaws.com', 'Dev', 'https://xyz789.execute-api.us-east-1.amazonaws.com/Dev'),
        ('abc123.execute-api.us-east-1.amazonaws.com', 'Prod', 'https://abc123.execute-api.us-east-1.amazonaws.com/Prod'),
    ],
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
    'domain, stage, expected',
    [
        ('lambda.hello.com', 'Dev', 'https://lambda.hello.com'),
        ('example.com', 'Prod', 'https://example.com'),
    ],
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


@pytest.mark.parametrize(
    'event',
    [
        {'requestContext': {}},
        {'requestContext': {'domainName': ''}},
        {'requestContext': {'stage': 'Dev'}},
    ],
)
def test_base_url_handles_incomplete_context(event):
    """Ensure base_url() gracefully falls back when requestContext is incomplete."""
    result = base_url(event)
    assert result == 'http://localhost:3000'


# -------------------------------
# 2. Get short url string representation
# -------------------------------


@pytest.mark.parametrize(
    'shortcode, domain, stage, expected',
    [
        ('abc123', 'lambda.hello.com', 'Prod', 'https://lambda.hello.com/abc123'),
        ('xyz789', 'lambda.hello.com', 'Prod', 'https://lambda.hello.com/xyz789'),
        ('abc123', 'lambda.api.com', 'Prod', 'https://lambda.api.com/abc123'),
    ],
)
def test_get_short_url(shortcode, domain, stage, expected):
    """Ensure get_short_url() returns the correct short URL string."""
    event = {
        'requestContext': {
            'domainName': domain,
            'stage': stage,
        }
    }
    result = get_short_url(shortcode, event)
    assert result == expected


# -------------------------------
# 3. beginning_of_next_month() computation
# -------------------------------


@pytest.mark.parametrize(
    'frozen_date, expected',
    [
        ('2025-01-15', datetime(2025, 2, 1, 0, 0, 0, tzinfo=UTC)),
        ('2025-02-28', datetime(2025, 3, 1, 0, 0, 0, tzinfo=UTC)),
        ('2025-10-15', datetime(2025, 11, 1, 0, 0, 0, tzinfo=UTC)),
        ('2025-11-30', datetime(2025, 12, 1, 0, 0, 0, tzinfo=UTC)),
        ('2025-12-31', datetime(2026, 1, 1, 0, 0, 0, tzinfo=UTC)),
        ('2024-02-29', datetime(2024, 3, 1, 0, 0, 0, tzinfo=UTC)),
    ],
)
def test_beginning_of_next_month(frozen_date, expected):
    """Ensure beginning_of_next_month() computes the correct next month's first moment."""
    with freeze_time(frozen_date):
        result = beginning_of_next_month()
        assert result == expected


# -------------------------------
# 4.1. require_environment() happy path
# -------------------------------


def test_require_environment_happy_path(monkeypatch):
    """4.1. Decorated function executes when all env vars are present."""
    monkeypatch.setenv('ENV1', 'value1')
    monkeypatch.setenv('ENV2', 'value2')

    @require_environment('ENV1', 'ENV2')
    def sample_function(x: int) -> int:
        return x + 1

    assert sample_function(1) == 2


# -------------------------------
# 4.2. require_environment() missing or empty env vars
# -------------------------------


@pytest.mark.parametrize(
    'env_setup, missing_names',
    [
        ({'ENV1': None, 'ENV2': 'value2'}, ["'ENV1'"]),
        ({'ENV1': '', 'ENV2': 'value2'}, ["'ENV1'"]),
        ({'ENV1': None, 'ENV2': None}, ["'ENV1'", "'ENV2'"]),
        ({'ENV1': '', 'ENV2': ''}, ["'ENV1'", "'ENV2'"]),
    ],
)
def test_require_environment_missing_or_empty(monkeypatch, env_setup, missing_names):
    """4.2. Missing or empty env vars raise a descriptive ValueError."""
    for name, value in env_setup.items():
        if value is None:
            monkeypatch.delenv(name, raising=False)
        else:
            monkeypatch.setenv(name, value)

    @require_environment('ENV1', 'ENV2')
    def sample_function() -> None:
        pass

    expected_message = f'Missing required environment variables: {", ".join(missing_names)}'
    with pytest.raises(KeyError, match=expected_message):
        sample_function()


# -------------------------------
# 5. guarantee_500_response() behavior
# -------------------------------


def test_guarantee_500_response(monkeypatch):
    """5.1. Faulty lambda handler returns 500 response when not running locally."""
    monkeypatch.setattr('cloudshortener.utils.helpers.running_locally', lambda: False)

    @guarantee_500_response
    def faulty_lambda_handler(event, context):
        raise RuntimeError('boom')

    response = faulty_lambda_handler({}, None)
    body = json.loads(response['body'])

    assert response['statusCode'] == 500
    assert isinstance(body, dict)
    assert body['message'] == 'Internal Server Error'
    assert body['error_code'] == 'UNKNOWN_INTERNAL_SERVER_ERROR'


def test_guarantee_500_response_reraises_when_running_locally(monkeypatch):
    """5.2. Faulty lambda handler reraises the original exception when running locally."""
    monkeypatch.setattr('cloudshortener.utils.helpers.running_locally', lambda: True)

    @guarantee_500_response
    def faulty_lambda_handler(event, context):
        raise RuntimeError('boom')

    with pytest.raises(RuntimeError, match='boom'):
        faulty_lambda_handler({}, None)
