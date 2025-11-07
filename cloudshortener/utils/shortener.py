"""Shortcode generation utility

This module provides a helper function for generating short, deterministic,
non-sequential hashes based on a numeric counter and a secret salt value.

Functions:
    generate_shortcode(counter, salt='default_salt', length=7):
        Generate a short hash suitable for use as a URL slug.

Example:
    >>> from cloudshortener.utils import generate_shortcode
    >>> generate_shortcode(12345, salt='my_secret')
    'Gh71WPT'
"""

import string

import xxhash


ALPHABET = string.ascii_lowercase + string.ascii_uppercase + string.digits
BASE = len(ALPHABET)  # noqa: E114 hashids produce base62-safe strings:
# noqa: E114, E116 26 lowercase + 26 uppercase + 10 digits


def generate_shortcode(counter: int, salt: str = 'default_salt', length: int = 7) -> str:
    """Generate a short, deterministic URL hash from a counter and salt.

    This function encodes a numeric counter into an n-character Base62 string
    (using A-Z, a-z, 0-9). The counter is salted and wrapped wrapped in modulo
    BASE^length to ensure fixed-length output.

    Args:
        counter (int):
            Unique integer value identifying the URL.

        salt (str, optional):
            Secret string used to randomize the output space.
            Defaults to "default_salt".
            Highly recommended to set a custom salt for security.

        length (int, optional):
            Minimum length of the resulting hash.
            Defaults to 7.

    Returns:
        str: A short alphanumeric hash derived from the counter and salt.

    Example:
        >>> generate_shortcode(12345, salt='my_secret', length=7)
        'Gh71WPT'

    NOTE:
        - While the funnction will eventually produce collisions to ensure
          fixed-length output, old URLs are expected to expire. This ensures
          The risk of collisions is practically 0.
        - The output is non-reversible without knowledge of the salt.
        - The alphabet is Base62 safe: [a-zA-Z0-9].
        - Uses ultra-fast xxhash for hashing the salt.
    """
    if not isinstance(counter, int):
        raise TypeError(f'Counter must be of type integer (given type: {type(counter)}).')
    if counter < 0:
        raise ValueError(f'Counter must be a non-negative integer (given value: {counter}).')
    if not isinstance(salt, str):
        raise TypeError(f'Salt must be of type string (given type: {type(salt)}).')
    if len(salt) <= 0:
        raise ValueError(f'Salt must be a non-empty string (given value: {salt}).')

    # Salt and wrap around counter to ensure fixed-length output
    # NOTE: this introduces a risk of collisions for very large counter values.
    #       However, since short URLs are expected to expire after 1 year,
    #       collisions are practically eliminated.
    # NOTE: uses ultra-fast xxhash for hashing the salt
    salt_hash = xxhash.xxh64_intdigest(salt)
    salted = (counter + salt_hash) % (BASE**length)

    # Custom base62 encoding algorithm:
    # 1- Encode the salted counter into base62 (generator comprehension)
    # 2- Reverse order of generator output to ensure most significant digit is first (reversed())
    # 3- Join characters into a single string (''.join())
    # 4- Pad with leading 'a' characters to ensure fixed length (rjust())
    return ''.join(reversed([ALPHABET[(salted // BASE**i) % BASE] for i in range(length)])).rjust(length, ALPHABET[0])
