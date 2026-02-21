"""Unit tests for runtime utilities in runtime.py."""

import re
import pytest

from cloudshortener.utils.runtime import running_locally, get_user_id
from cloudshortener.constants import ENV


@pytest.mark.parametrize(
    'app_env, sam_flag, expected',
    [
        ('local', None, True),
        ('dev', None, False),
        ('dev', 'true', True),
    ],
)
def test_running_locally(monkeypatch, app_env, sam_flag, expected):
    monkeypatch.setenv(ENV.App.APP_ENV, app_env)

    if sam_flag is None:
        monkeypatch.delenv(ENV.App.AWS_SAM_LOCAL, raising=False)
    else:
        monkeypatch.setenv(ENV.App.AWS_SAM_LOCAL, sam_flag)

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
    monkeypatch.setenv(ENV.App.AWS_SAM_LOCAL, 'true')
    user_id = get_user_id({})
    assert user_id is not None
    assert re.match(r'lambda\d{3}', user_id)
