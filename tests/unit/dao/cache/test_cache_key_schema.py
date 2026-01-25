"""Unit tests for the CacheKeySchema class in cache_key_schema.py.

This test suite verifies the correctness, consistency, and safety of
cache key generation supplied by CacheKeySchema for AppConfig caching.

Test coverage includes:
    1. AppConfig keys generation
       - Ensures the appconfig_* key methods generate correct cache keys.
    2. Default prefix behavior
       - Confirms keys are not prefixed when no prefix is provided.
    3. Custom prefix behavior
       - Confirms keys are correctly prefixed when a valid prefix is provided.
    4. Invalid prefix types
       - Ensures improper prefix types raise TypeError.
    5. Invalid version types
       - Ensures version arguments are validated (cast to int) and invalid inputs raise.
"""

import pytest

from cloudshortener.dao.cache.cache_key_schema import CacheKeySchema


# -------------------------------
# Pytest fixtures
# -------------------------------


@pytest.fixture
def keys():
    return CacheKeySchema()


# -------------------------------
# 1. AppConfig keys generation
# -------------------------------


def test_appconfig_latest_key(keys):
    """Ensure appconfig_latest_key() generates correct latest document key."""
    assert keys.appconfig_latest_key() == 'appconfig:latest'


def test_appconfig_latest_metadata_key(keys):
    """Ensure appconfig_latest_metadata_key() generates correct metadata key."""
    assert keys.appconfig_latest_metadata_key() == 'appconfig:latest:metadata'


@pytest.mark.parametrize(
    'version, expected',
    [
        (1, 'appconfig:v1'),
        (12, 'appconfig:v12'),
        (999, 'appconfig:v999'),
    ],
)
def test_appconfig_version_key(version, expected, keys):
    """Ensure appconfig_version_key() generates valid cache keys."""
    assert keys.appconfig_version_key(version) == expected


@pytest.mark.parametrize(
    'version, expected',
    [
        (1, 'appconfig:v1:metadata'),
        (7, 'appconfig:v7:metadata'),
        (42, 'appconfig:v42:metadata'),
    ],
)
def test_appconfig_metadata_key(version, expected, keys):
    """Ensure appconfig_metadata_key() generates valid cache keys."""
    assert keys.appconfig_metadata_key(version) == expected


# -------------------------------
# 2. Default prefix behavior
# -------------------------------


def test_no_prefix_by_default(keys):
    """Ensure keys are not prefixed when no prefix is provided."""
    assert keys.appconfig_latest_key() == 'appconfig:latest'
    assert keys.appconfig_latest_metadata_key() == 'appconfig:latest:metadata'
    assert keys.appconfig_version_key(5) == 'appconfig:v5'
    assert keys.appconfig_metadata_key(5) == 'appconfig:v5:metadata'


# -------------------------------
# 3. Custom prefix behavior
# -------------------------------


# fmt: off
@pytest.mark.parametrize(
    'prefix, version, expected_latest, expected_latest_meta, expected_version, expected_meta',
    [
        ('cloudshortener:dev', 3,
         'cache:cloudshortener:dev:appconfig:latest',
         'cache:cloudshortener:dev:appconfig:latest:metadata',
         'cache:cloudshortener:dev:appconfig:v3',
         'cache:cloudshortener:dev:appconfig:v3:metadata'),
        ('testprefix', 10,
         'cache:testprefix:appconfig:latest',
         'cache:testprefix:appconfig:latest:metadata',
         'cache:testprefix:appconfig:v10',
         'cache:testprefix:appconfig:v10:metadata'),
        (None, 5,
         'appconfig:latest',
         'appconfig:latest:metadata',
         'appconfig:v5',
         'appconfig:v5:metadata'),
    ],
)
# fmt: on
def test_prefix_behavior(prefix, version, expected_latest, expected_latest_meta, expected_version, expected_meta):
    """Ensure AppConfig keys are correctly prefixed when a prefix is provided."""
    keys = CacheKeySchema(prefix=prefix)
    assert keys.appconfig_latest_key() == expected_latest
    assert keys.appconfig_latest_metadata_key() == expected_latest_meta
    assert keys.appconfig_version_key(version) == expected_version
    assert keys.appconfig_metadata_key(version) == expected_meta


# -------------------------------
# 4. Invalid prefix types
# -------------------------------


@pytest.mark.parametrize('prefix', [123, -1, 45.6, [], {}])
def test_invalid_prefix_type_raises_error(prefix):
    """Ensure invalid prefix types raise a TypeError."""
    with pytest.raises(TypeError):
        CacheKeySchema(prefix=prefix)


# -------------------------------
# 5. Invalid version types
# -------------------------------


@pytest.mark.parametrize('invalid_version', ['abc', None, [], {}])
def test_invalid_version_type_raises_error(invalid_version, keys):
    """Ensure invalid version types raise an error when cast to int."""
    with pytest.raises((TypeError, ValueError)):
        keys.appconfig_version_key(invalid_version)
    with pytest.raises((TypeError, ValueError)):
        keys.appconfig_metadata_key(invalid_version)
