"""Unit tests for the ShortURLModel dataclass in short_url_model.py.

This test suite verifies the integrity, immutability, and equality behavior
of the ShortURLModel, which represents a shortened URL mapping with an
optional expiration timestamp.

Test coverage includes:

1. Model creation and field validation
   - Ensures instances can be created with valid field types and values.

2. Optional expires_at field
   - Verifies that expires_at can be omitted and defaults to None.

3. Equality semantics
   - Confirms that models with identical data compare equal.

4. Inequality semantics
   - Ensures that differing field values (URL, short code, or expiration)
     produce non-equal instances.

5. Immutability
   - Verifies that all fields are frozen and cannot be reassigned after
     object creation.
"""

from dataclasses import FrozenInstanceError
from datetime import datetime

import pytest

from cloudshortener.models.short_url_model import ShortURLModel


# -------------------------------------------------
# 1. Model creation and field type validation
# -------------------------------------------------

def test_valid_short_url_model_creation():
    """Ensure ShortURLModel can be created with valid data and types."""
    original_url = "https://example.com/article/123"
    shortcode = "abc123"
    hits=10000
    expires_at = datetime(2026, 1, 1, 0, 0, 0)  # 1st Jan 2026 00:00:00

    short_url = ShortURLModel(
        target=original_url,
        shortcode=shortcode,
        hits=hits,
        expires_at=expires_at,
    )

    assert isinstance(short_url, ShortURLModel)
    assert isinstance(short_url.target, str)
    assert short_url.target == original_url
    assert isinstance(short_url.shortcode, str)
    assert short_url.shortcode == shortcode
    assert isinstance(short_url.hits, int)
    assert short_url.hits == hits 
    assert isinstance(short_url.expires_at, datetime)
    assert short_url.expires_at == expires_at


# -------------------------------------------------
# 2. Optional fields
# -------------------------------------------------

def test_hits_is_optional():
    """Verify that hits can be omitted and defaults to None."""
    short_url = ShortURLModel(
        target='https://example.com/article/123',
        shortcode='abc123',
    )

    assert isinstance(short_url, ShortURLModel)
    assert short_url.hits is None


def test_expires_at_is_optional():
    """Verify that expires_at can be omitted and defaults to None."""
    short_url = ShortURLModel(
        target="https://example.com/article/123",
        shortcode="abc123",
    )

    assert isinstance(short_url, ShortURLModel)
    assert short_url.expires_at is None


# -------------------------------------------------
# 3. Equality semantics
# -------------------------------------------------

def test_short_url_model_equality():
    """Models with identical data should compare equal."""
    expires_at = datetime(2026, 1, 1, 0, 0, 0)

    short_url1 = ShortURLModel(
        target="https://example.com/article/123",
        shortcode="abc123",
        hits=10000,
        expires_at=expires_at,
    )

    short_url2 = ShortURLModel(
        target="https://example.com/article/123",
        shortcode="abc123",
        hits=10000,
        expires_at=expires_at,
    )

    assert short_url1 == short_url2
    assert short_url1.target == short_url2.target
    assert short_url1.shortcode == short_url2.shortcode
    assert short_url1.hits == short_url2.hits
    assert short_url1.expires_at == short_url2.expires_at


# -------------------------------------------------
# 4. Inequality semantics
# -------------------------------------------------

@pytest.mark.parametrize(
    'right_url_parameters',
    [
        {
            'target': 'https://example.com/article/456',
            'shortcode': 'abc123',
            'hits': 10000,
            'expires_at': datetime(2026, 1, 1, 0, 0, 0),
        },
        {
            'target': 'https://example.com/article/123',
            'shortcode': 'def456',
            'hits': 10000,
            'expires_at': datetime(2026, 1, 1, 0, 0, 0),
        },
        {
            'target': 'https://example.com/article/123',
            'shortcode': 'abc123',
            'hits': 2000,
            'expires_at': datetime(2026, 1, 1, 0, 0, 0),
        },
        {
            'target': 'https://example.com/article/123',
            'shortcode': 'abc123',
            'hits': 10000,
            'expires_at': datetime(2027, 1, 1, 0, 0, 0),
        },
    ],
)
def test_short_url_model_inequality(right_url_parameters):
    """Models with differing data should not compare equal."""
    left_url = ShortURLModel(
        target="https://example.com/article/123",
        shortcode="abc123",
        hits=10000,
        expires_at=datetime(2026, 1, 1, 0, 0, 0),
    )

    right_url = ShortURLModel(**right_url_parameters)

    assert left_url != right_url


# -------------------------------------------------
# 5. Immutability
# -------------------------------------------------

@pytest.mark.parametrize(
    'field, new_value',
    [
        ('target', 'https://example.com/article/456'),
        ('shortcode', 'def456'),
        ('hits', 3000),
        ('expires_at', datetime(2027, 1, 1, 0, 0, 0)),
    ],
)
def test_short_url_model_immutability(field, new_value):
    """Attempting to modify fields should raise FrozenInstanceError."""
    short_url = ShortURLModel(
        target='https://example.com/article/123',
        shortcode='abc123',
        hits=10000,
        expires_at=datetime(2026, 1, 1, 0, 0, 0),
    )

    with pytest.raises(FrozenInstanceError):
        setattr(short_url, field, new_value)
