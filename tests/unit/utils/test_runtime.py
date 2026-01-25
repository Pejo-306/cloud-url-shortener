"""Unit tests for runtime utilities in runtime.py.

Test coverage includes:
    1. running_locally() behavior
    2. get_user_id() behavior
"""

import re
import pytest

from cloudshortener.utils.runtime import running_locally, get_user_id
from cloudshortener.utils.constants import APP_ENV_ENV, AWS_SAM_LOCAL_ENV


@pytest.mark.parametrize(
    'app_env, sam_flag, expected',
    [
        ('local', None, True),
        ('dev', None, False),
        ('dev', 'true', True),
    ],
)
def test_running_locally(monkeypatch, app_env, sam_flag, expected):
    """running_locally() evaluates local execution correctly."""
    monkeypatch.setenv(APP_ENV_ENV, app_env)

    if sam_flag is None:
        monkeypatch.delenv(AWS_SAM_LOCAL_ENV, raising=False)
    else:
        monkeypatch.setenv(AWS_SAM_LOCAL_ENV, sam_flag)

    assert running_locally() is expected


@pytest.mark.parametrize(
    'event, expected',
    [
        ({'requestContext': {'authorizer': {'claims': {'sub': 'lambda123'}}}}, 'lambda123'),
        ({'requestContext': {'authorizer': {'claims': {'sub': 'lambda456'}}}}, 'lambda456'),
        ({'requestContext': {'authorizer': {'claims': {'sub': None}}}}, None),
    ],
)
def test_get_user_id(event, expected):
    """get_user_id() returns the user id from the event."""
    assert get_user_id(event) == expected


def test_get_user_id_with_local_sam_api(monkeypatch):
    """get_user_id() returns a random user id if the lambda runs locally via sam local invoke."""
    monkeypatch.setenv(AWS_SAM_LOCAL_ENV, 'true')
    assert re.match(r'lambda\d{3}', get_user_id({}))
