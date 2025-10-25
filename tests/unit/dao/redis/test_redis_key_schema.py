"""Unit tests for the RedisKeySchema class in redis_key_schema.py.

This test suite verifies the correctness, consistency, and safety of 
Redis key generation supplied by RedisKeySchema.

Test coverage includes:

1. Link URL key generation
   - Ensures link_url_key() generates correct Redis keys for a given shortcode.

2. Link hits key generation
   - Ensures link_hits_key() generates correct Redis keys for a given shortcode.

3. Default prefix behavior
   - Confirms keys are not prefixed when no prefix is provided.

4. Custom prefix behavior
   - Confirms keys are correctly prefixed when a valid prefix is provided.

5. Invalid prefix types
   - Ensures improper prefix types raise TypeError.
"""

import pytest

from cloudshortener.dao.redis.redis_key_schema import RedisKeySchema


# -------------------------------
# 1. Link URL key generation
# -------------------------------

@pytest.mark.parametrize(
    "shortcode, expected",
    [
        ("abc123", "links:abc123:url"),
        ("XyZ789", "links:XyZ789:url"),
    ],
)
def test_link_url_key(shortcode, expected):
    """Ensure link_url_key() generates valid Redis keys."""
    keys = RedisKeySchema()
    result = keys.link_url_key(shortcode)
    assert result == expected


# -------------------------------
# 2. Link hits key generation
# -------------------------------

@pytest.mark.parametrize(
    "shortcode, expected",
    [
        ("abc123", "links:abc123:hits"),
        ("XyZ789", "links:XyZ789:hits"),
    ],
)
def test_link_hits_key(shortcode, expected):
    """Ensure link_hits_key() generates valid Redis keys."""
    keys = RedisKeySchema()
    result = keys.link_hits_key(shortcode)
    assert result == expected


# -------------------------------
# 3. Default prefix behavior
# -------------------------------

def test_no_key_prefix_by_default():
    """Ensure keys are not prefixed when no prefix is provided."""
    keys = RedisKeySchema()
    url_key = keys.link_url_key("abc123")
    hits_key = keys.link_hits_key("abc123")
    assert url_key == "links:abc123:url"
    assert hits_key == "links:abc123:hits"


# -------------------------------
# 4. Custom prefix behavior
# -------------------------------

@pytest.mark.parametrize(
    "prefix, shortcode, expected_url_key, expected_hits_key",
    [
        ("testprefix", "abc123", "testprefix:links:abc123:url", "testprefix:links:abc123:hits"),
        ("secret", "abc123", "secret:links:abc123:url", "secret:links:abc123:hits"),
        (None, "abc123", "links:abc123:url", "links:abc123:hits"),
    ],
)
def test_key_prefixing(prefix, shortcode, expected_url_key, expected_hits_key):
    """Ensure keys are correctly prefixed when a prefix is provided."""
    keys = RedisKeySchema(prefix=prefix)
    url_key = keys.link_url_key(shortcode)
    hits_key = keys.link_hits_key(shortcode)
    assert url_key == expected_url_key
    assert hits_key == expected_hits_key


# -------------------------------
# 5. Invalid prefix types
# -------------------------------

@pytest.mark.parametrize("prefix", [123, -1, 45.6, [], {}])
def test_invalid_prefix_type_raises_error(prefix):
    """Ensure invalid prefix types raise a TypeError."""
    with pytest.raises(TypeError):
        RedisKeySchema(prefix=prefix)

