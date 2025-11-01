"""Unit tests for the generate_shortcode function in shortener.py.

This test suite verifies the correctness, consistency, and robustness
of the generate_shortcode() helper function that generates deterministic,
base62-safe short hashes using the Hashids algorithm.

Test coverage includes:

1. Basic functionality
   - Ensures the function returns a string of the expected length.

2. Determinism
   - Same input and salt must always produce identical output.

3. Different salts
   - Changing the salt for the same counter produces different results.

4. Edge cases
   - Handles small, zero, and very large integer counters gracefully.
   - Ensures wrapped, fixed-length output even for large counter values.

5. Error handling
   - Ensures invalid inputs (negative numbers, non-integers, None) raise
     appropriate exceptions.

6. Output format
   - All characters in the hash must belong to the Base62 alphabet
     (letters and digits only).

7. Length parameter enforcement
   - The 'length' argument must be respected; output should meet or exceed
     the specified minimum length.

8. Regression testing
   - Known input and salt combinations produce stable, expected output
     to detect accidental future changes.

9. Performance sanity
    - The function executes efficiently for a large number of iterations.
"""

import string
import time

import pytest

from cloudshortener.utils import generate_shortcode


# -------------------------------
# 1. Basic functionality and type
# -------------------------------

def test_shorten_url_returns_string():
    """Ensure generate_shortcode() returns a string of the expected length."""
    result = generate_shortcode(123, salt='unit_test_salt', length=7)
    assert isinstance(result, str)
    assert len(result) == 7
    assert result == 'XrJQsJI'


# -------------------------------
# 2. Determinism
# -------------------------------

def test_shorten_url_is_deterministic():
    """Same counter + same salt should always produce the same hash."""
    result1 = generate_shortcode(123, salt='unit_test_salt')
    result2 = generate_shortcode(123, salt='unit_test_salt')
    assert result1 == result2
    assert result1 == 'XrJQsJI'
    assert result2 == 'XrJQsJI'


# -------------------------------
# 3. Salt variation
# -------------------------------

def test_shorten_url_diff_salts_produce_diff_hashes():
    """Changing the salt must produce different hashes for the same counter."""
    result1 = generate_shortcode(123, salt='unit_test_saltA')
    result2 = generate_shortcode(123, salt='unit_test_saltB')
    assert result1 != result2
    assert result1 == 'Nr5bkci'
    assert result2 == 'q7femOj'


# -------------------------------
# 4. Edge cases
# -------------------------------

@pytest.mark.parametrize('counter', [0, 1, 10**6, 2**63 - 1])
def test_shorten_url_handles_edge_counters(counter):
    """Ensure small and large counter values always produce a 7-character short URL."""
    result = generate_shortcode(counter, salt='edge_test')
    assert isinstance(result, str)
    assert len(result) == 7


def test_shorten_url_wraps_around_for_big_counter_values():
    """Ensure very large counter values wrap around to maintain fixed-length output."""
    result1 = generate_shortcode(12345, salt='my_secret', length=7)
    result2 = generate_shortcode(62**7 + 12345, salt='my_secret', length=7)
    result3 = generate_shortcode(2 * 62**7 + 12345, salt='my_secret', length=7)
    assert len(result1) == 7
    assert len(result2) == 7
    assert len(result3) == 7
    assert result1 == 'Gh71WPT'
    assert result2 == 'Gh71WPT'
    assert result3 == 'Gh71WPT'


# -------------------------------
# 5. Error handling
# -------------------------------

@pytest.mark.parametrize('counter', [None, 'abc', 12.34])
def test_invalid_counter_type_raises_error(counter):
    """Non-integer counters raise TypeError."""
    with pytest.raises(TypeError):
        generate_shortcode(counter, salt='unit_test_salt')


@pytest.mark.parametrize('counter', [-1])
def test_invalid_counter_value_raises_error(counter):
    """Negative counters should raise ValueError."""
    with pytest.raises(ValueError):
        generate_shortcode(counter, salt='unit_test_salt')


@pytest.mark.parametrize('salt', [None, 1, -1, 12.34])
def test_invalid_salt_type_raises_error(salt):
    """Empty or None salt raise a ValueError."""
    with pytest.raises(TypeError):
        generate_shortcode(100, salt=salt)


@pytest.mark.parametrize('salt', [''])
def test_empty_or_none_salt_raises_error(salt):
    """Empty or None salt raise a ValueError."""
    with pytest.raises(ValueError):
        generate_shortcode(100, salt=salt)


# -------------------------------
# 6. Output format validation
# -------------------------------

def test_shorten_url_is_base62_safe():
    """Ensure output contains only Base62-safe characters."""
    alphabet = set(string.ascii_letters + string.digits)
    result = generate_shortcode(123, salt='format_test')
    assert all(character in alphabet for character in result)


# -------------------------------
# 7. Length enforcement
# -------------------------------

def test_shorten_url_respects_length():
    """Ensure output meets or exceeds the requested minimum length."""
    result = generate_shortcode(12345, salt='length_test', length=10)
    assert len(result) == 10


# -------------------------------
# 8. Regression test
# -------------------------------

def test_known_output_regression():
    """Ensure stable output for known inputs (detect logic drift)."""
    expected = 'Gh71WPT'
    assert generate_shortcode(12345, salt='my_secret', length=7) == expected


# -------------------------------
# 9. Performance sanity check
# -------------------------------

@pytest.mark.parametrize('iterations', [40, 400, 4000, 40000])
def test_shorten_url_performance(iterations):
    """Ensure the function runs efficiently for multiple iterations.
    
    NOTE: The system must be able to handle 40 link generations per second.
          The size of iterations parameter demonstrates that the URL shortening
          function will not cause a bottleneck in performance.
    """
    start = time.perf_counter()
    for i in range(iterations):
        generate_shortcode(i, salt="perf_salt")
    duration = time.perf_counter() - start
    assert duration < 1.0  # Must complete within 1 second for given iterations
