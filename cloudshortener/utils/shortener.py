"""Shortcode generation utility

This module provides a helper function for generating short, deterministic,
non-sequential hashes based on a numeric counter and a secret salt value.

Functions:
    generate_shortcode(counter, salt='default_salt', length=7, mult=1315423911):
        Generate a short hash suitable for use as a URL slug.

Example:
    >>> from cloudshortener.utils import generate_shortcode
    >>> generate_shortcode(12345, salt='my_secret')
    'ibCJIAD'
"""

import math
import string

import xxhash


ALPHABET = string.ascii_lowercase + string.ascii_uppercase + string.digits
BASE = len(ALPHABET)  # noqa: E114 hashids produce base62-safe strings:
# noqa: E114, E116 26 lowercase + 26 uppercase + 10 digits


def generate_shortcode(counter: int, salt: str = 'default_salt', length: int = 7, mult: int = 1315423911) -> str:
    """Generate a short, deterministic URL hash from a counter and salt.

    This function encodes a numeric counter into an n-character Base62 string
    (using A-Z, a-z, 0-9). The counter is salted and wrapped wrapped in modulo
    BASE^length to ensure fixed-length output.

    This implementation uses a **multiplicative permutation** over a fixed
    Base62 space to guarantee:
    - 1:1 mapping (bijective)
    - Deterministic output
    - No visible sequential patterns
    - Constant-time execution

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

        mult (int, optional):
            Multiplicative factor for the permutation.
            Defaults to 1315423911.
            Must be coprime with mod (BASE**length).

    Returns:
        str: A short alphanumeric hash derived from the counter and salt.

    Example:
        >>> generate_shortcode(12345, salt='my_secret', length=7)
        'Gh71WPT'

    NOTE:
        - While the funnction will eventually produce collisions to ensure
          fixed-length output, old URLs are expected to expire. This ensures
          The risk of collisions is practically 0.
        - The output is not trivially predictable without knowledge of the salt
          and permutation parameters (this is obfuscation, not encryption).
        - The alphabet is Base62 safe: [a-zA-Z0-9].
        - Uses ultra-fast xxhash for hashing the salt.
    """
    if not isinstance(counter, int):
        raise TypeError(f'Counter must be of type integer (given type: {type(counter)}).')
    if counter < 0:
        raise ValueError(f'Counter must be a non-negative integer (given value: {counter}).')
    if not isinstance(salt, str):
        raise TypeError(f'Salt must be of type string (given type: {type(salt)}).')
    if not salt:
        raise ValueError(f'Salt must be a non-empty string (given value: {salt}).')
    if math.gcd(mult, BASE**length) != 1:
        raise ValueError(f'Multiplicative factor must be coprime with mod ({BASE**length}) (given value: mult={mult}).')

    # Apply an affine (multiplicative + additive) permutation over the fixed
    # modulo space to scramble sequential counters while preserving a 1:1 mapping.
    # NOTE: This mapping is collision-free as long as `counter < BASE**length`.
    #       Collisions only occur after the counter wraps around the modulo space.
    #       Operationally, this is acceptable because short URLs are expected to
    #       expire before exhaustion of the ID space.
    # NOTE: uses ultra-fast xxhash for hashing the salt
    modulo_space = BASE**length
    salt_hash = xxhash.xxh64_intdigest(salt) % modulo_space
    permuted = (counter * mult + salt_hash) % modulo_space

    # Custom base62 encoding algorithm:
    # 1- Encode the permuted counter into base62 (generator comprehension)
    # 2- Reverse order of generator output to ensure most significant digit is first (reversed())
    # 3- Join characters into a single string (''.join())
    # 4- Pad with leading 'a' characters to ensure fixed length (rjust())
    return ''.join(reversed([ALPHABET[(permuted // BASE**i) % BASE] for i in range(length)])).rjust(length, ALPHABET[0])
