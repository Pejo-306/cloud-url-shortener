"""Unit tests for runtime utilities in runtime.py.

Test coverage includes:

1. running_locally() behavior
"""

import pytest

from cloudshortener.utils.runtime import running_locally
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
