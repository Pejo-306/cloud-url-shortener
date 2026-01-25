"""Unit tests for handle_redis_connection_error decorator.

This test suite verifies that the decorator properly handles Redis
connection failures and preserves the original method’s behavior.

Test coverage includes:
    1. Normal function execution
       - Ensures the wrapped method executes and returns its result.
    2. Connection error handling
       - Ensures Redis connection errors are converted into DataStoreError.
    3. Function metadata preservation
       - Confirms functools.wraps preserves the original function's name and docstring.
"""

import pytest
import redis
from unittest.mock import MagicMock

from cloudshortener.dao.redis.helpers import handle_redis_connection_error
from cloudshortener.dao.exceptions import DataStoreError


# -------------------------------
# 1. Normal execution
# -------------------------------


def test_decorator_allows_normal_execution():
    """Ensure the wrapped function executes normally when no error occurs."""

    class DummyDAO:
        def __init__(self):
            self.redis = MagicMock()

        @handle_redis_connection_error
        def ping(self):
            return 'OK'

    dao = DummyDAO()
    assert dao.ping() == 'OK'


# -------------------------------
# 2. Connection error handling
# -------------------------------


def test_decorator_transforms_redis_connection_error():
    """Ensure Redis ConnectionError is caught and re-raised as DataStoreError."""

    class DummyDAO:
        def __init__(self):
            self.redis = MagicMock()
            self.redis.connection_pool.connection_kwargs = {
                'host': 'localhost',
                'port': 6379,
                'db': 0,
            }

        @handle_redis_connection_error
        def fail(self):
            raise redis.exceptions.ConnectionError('Cannot connect')

    dao = DummyDAO()

    with pytest.raises(DataStoreError, match="Can't connect to Redis at localhost:6379/0."):
        dao.fail()


# -------------------------------
# 3. Function metadata preservation
# -------------------------------


def test_decorator_preserves_function_metadata():
    """Ensure function name and docstring are preserved via functools.wraps."""

    @handle_redis_connection_error
    def sample_function():
        """This is a sample docstring."""
        return 'OK'

    assert sample_function.__name__ == 'sample_function'
    assert 'sample docstring' in sample_function.__doc__
