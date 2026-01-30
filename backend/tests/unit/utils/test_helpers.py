"""Unit tests for helper functions in helpers.py."""

import json
from datetime import datetime, UTC
from typing import cast

import pytest
from pytest import MonkeyPatch
from freezegun import freeze_time

from cloudshortener.types import LambdaEvent
from cloudshortener.exceptions import MissingEnvironmentVariableError
from cloudshortener.utils.helpers import (
    base_url,
    get_short_url,
    beginning_of_next_month,
    require_environment,
    guarantee_500_response,
)


@pytest.mark.parametrize(
    'domain, stage, expected',
    [
        ('abc123.execute-api.us-east-1.amazonaws.com', 'Dev', 'https://abc123.execute-api.us-east-1.amazonaws.com/Dev'),
        ('xyz789.execute-api.us-east-1.amazonaws.com', 'Dev', 'https://xyz789.execute-api.us-east-1.amazonaws.com/Dev'),
        ('abc123.execute-api.us-east-1.amazonaws.com', 'Prod', 'https://abc123.execute-api.us-east-1.amazonaws.com/Prod'),
        ('lambda.hello.com', 'Dev', 'https://lambda.hello.com'),
        ('example.com', 'Prod', 'https://example.com'),
        ('localhost:3000', 'local', 'http://localhost:3000'),
        ('127.0.0.1:3000', 'local', 'http://127.0.0.1:3000'),
    ],
)
def test_base_url(domain: str, stage: str, expected: str) -> None:
    event = {
        'requestContext': {
            'domainName': domain,
            'stage': stage,
        }
    }
    result = base_url(event)
    assert result == expected


@pytest.mark.parametrize(
    'event',
    [
        {'requestContext': {}},
        {'requestContext': {'domainName': ''}},
        {'requestContext': {'stage': 'Dev'}},
    ],
)
def test_base_url_fallbacks_to_localhost(event: LambdaEvent) -> None:
    result = base_url(event)
    assert result == 'http://localhost:3000'


@pytest.mark.parametrize(
    'shortcode, domain, stage, expected',
    [
        ('abc123', 'lambda.hello.com', 'Prod', 'https://lambda.hello.com/abc123'),
        ('xyz789', 'lambda.hello.com', 'Prod', 'https://lambda.hello.com/xyz789'),
        ('abc123', 'lambda.api.com', 'Prod', 'https://lambda.api.com/abc123'),
    ],
)
def test_get_short_url(shortcode: str, domain: str, stage: str, expected: str) -> None:
    event = cast(
        LambdaEvent,
        {
            'requestContext': {
                'domainName': domain,
                'stage': stage,
            },
        },
    )
    result = get_short_url(shortcode, event)
    assert result == expected


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
def test_beginning_of_next_month(frozen_date: str, expected: datetime) -> None:
    """Ensure beginning_of_next_month() computes the correct next month's first moment."""
    with freeze_time(frozen_date):
        result = beginning_of_next_month()
        assert result == expected


def test_require_environment(monkeypatch: MonkeyPatch) -> None:
    monkeypatch.setenv('ENV1', 'value1')
    monkeypatch.setenv('ENV2', 'value2')

    @require_environment('ENV1', 'ENV2')
    def sample_function(x: int) -> int:
        return x + 1

    assert sample_function(1) == 2


@pytest.mark.parametrize(
    'env_setup, missing_names',
    [
        ({'ENV1': None, 'ENV2': 'value2'}, ["'ENV1'"]),
        ({'ENV1': '', 'ENV2': 'value2'}, ["'ENV1'"]),
        ({'ENV1': None, 'ENV2': None}, ["'ENV1'", "'ENV2'"]),
        ({'ENV1': '', 'ENV2': ''}, ["'ENV1'", "'ENV2'"]),
    ],
)
def test_require_environment_with_missing_or_empty_env_vars(
    monkeypatch: MonkeyPatch,
    env_setup: dict[str, str],
    missing_names: list[str],
) -> None:
    for name, value in env_setup.items():
        if value is None:
            monkeypatch.delenv(name, raising=False)
        else:
            monkeypatch.setenv(name, value)

    @require_environment('ENV1', 'ENV2')
    def sample_function() -> None:
        pass

    expected_message = f'Missing required environment variables: {", ".join(missing_names)}'
    with pytest.raises(MissingEnvironmentVariableError, match=expected_message):
        sample_function()


# TODO: extend this to include CORS headers
def test_guarantee_500_response(monkeypatch: MonkeyPatch) -> None:
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


def test_guarantee_500_response_reraises_when_running_locally(monkeypatch: MonkeyPatch) -> None:
    monkeypatch.setattr('cloudshortener.utils.helpers.running_locally', lambda: True)

    @guarantee_500_response
    def faulty_lambda_handler(event, context):
        raise RuntimeError('boom')

    with pytest.raises(RuntimeError, match='boom'):
        faulty_lambda_handler({}, None)
