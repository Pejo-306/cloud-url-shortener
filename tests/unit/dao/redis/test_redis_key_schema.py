"""Unit tests for the RedisKeySchema class in redis_key_schema.py.

This test suite verifies the correctness, consistency, and safety of
Redis key generation supplied by RedisKeySchema.

Test coverage includes:
    1. Redis keys generation
       - Ensures the various _key() methods generate correct Redis keys.
    2. Default prefix behavior
       - Confirms keys are not prefixed when no prefix is provided.
    3. Custom prefix behavior
       - Confirms keys are correctly prefixed when a valid prefix is provided.
    4. Invalid prefix types
       - Ensures improper prefix types raise TypeError.
"""

import pytest
from freezegun import freeze_time

from cloudshortener.dao.redis.redis_key_schema import RedisKeySchema


# -------------------------------
# Pytest fixtures
# -------------------------------


@pytest.fixture
def keys():
    return RedisKeySchema()


# -------------------------------
# 1. Link URL key generation
# -------------------------------


@pytest.mark.parametrize(
    'shortcode, expected',
    [
        ('abc123', 'links:abc123:url'),
        ('XyZ789', 'links:XyZ789:url'),
    ],
)
def test_link_url_key(shortcode, expected):
    """Ensure link_url_key() generates valid Redis keys."""
    keys = RedisKeySchema()
    result = keys.link_url_key(shortcode)
    assert result == expected


@pytest.mark.parametrize(
    'shortcode, todays_date, expected',
    [
        ('abc123', '2025-10-15', 'links:abc123:hits:2025-10'),
        ('XyZ789', '2025-10-15', 'links:XyZ789:hits:2025-10'),
        ('XyZ789', '2024-01-01', 'links:XyZ789:hits:2024-01'),
    ],
)
def test_link_hits_key(shortcode, todays_date, expected):
    """Ensure link_hits_key() generates valid Redis keys."""
    keys = RedisKeySchema()
    with freeze_time(todays_date):
        result = keys.link_hits_key(shortcode)
    assert result == expected


def test_counter_key():
    """Ensure counter_key() generates valid Redis key for link counter."""
    keys = RedisKeySchema()
    result = keys.counter_key()
    assert result == 'links:counter'


@pytest.mark.parametrize(
    'user_id, todays_date, expected',
    [
        ('user123', '2025-11-10', 'users:user123:quota:2025-11'),
        ('User710', '2025-11-23', 'users:User710:quota:2025-11'),
        ('pesho', '2024-01-01', 'users:pesho:quota:2024-01'),
    ],
)
def test_user_quota_key(user_id, todays_date, expected, keys):
    with freeze_time(todays_date):
        result = keys.user_quota_key(user_id)
        assert result == expected


# -------------------------------
# 2. Default prefix behavior
# -------------------------------


@freeze_time('2025-10-15')
def test_no_key_prefix_by_default():
    """Ensure keys are not prefixed when no prefix is provided."""
    keys = RedisKeySchema()
    url_key = keys.link_url_key('abc123')
    hits_key = keys.link_hits_key('abc123')
    assert url_key == 'links:abc123:url'
    assert hits_key == 'links:abc123:hits:2025-10'


# -------------------------------
# 3. Custom prefix behavior
# -------------------------------


@pytest.mark.parametrize(
    'prefix, shortcode, expected_url_key, expected_hits_key',
    [
        ('testprefix', 'abc123', 'testprefix:links:abc123:url', 'testprefix:links:abc123:hits:2025-10'),
        ('secret', 'abc123', 'secret:links:abc123:url', 'secret:links:abc123:hits:2025-10'),
        (None, 'abc123', 'links:abc123:url', 'links:abc123:hits:2025-10'),
    ],
)
@freeze_time('2025-10-15')
def test_key_prefixing(prefix, shortcode, expected_url_key, expected_hits_key):
    """Ensure keys are correctly prefixed when a prefix is provided."""
    keys = RedisKeySchema(prefix=prefix)
    url_key = keys.link_url_key(shortcode)
    hits_key = keys.link_hits_key(shortcode)
    assert url_key == expected_url_key
    assert hits_key == expected_hits_key


# -------------------------------
# 4. Invalid prefix types
# -------------------------------


@pytest.mark.parametrize('prefix', [123, -1, 45.6, [], {}])
def test_invalid_prefix_type_raises_error(prefix):
    """Ensure invalid prefix types raise a TypeError."""
    with pytest.raises(TypeError):
        RedisKeySchema(prefix=prefix)
