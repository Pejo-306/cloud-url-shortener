# TODO: we can probably store the error code
# inside these exceptions instead of passing it to logger statements


class DAOError(Exception):
    """Generic base class for DAO-related exceptions."""


class ShortURLNotFoundError(DAOError):
    """Raised when a ShortURLModel is not found in the data store."""


class ShortURLAlreadyExistsError(DAOError):
    """Raised when inserting a ShortURLModel that already exists in the data store."""


class DataStoreError(DAOError):
    """Raised when the data store encounters an error.

    Examples include connection issues, timeouts, and out-of-memory failures.
    """


class UserDoesNotExistError(DAOError):
    """Raised when a user is not found in the data store."""


class CacheMissError(DAOError):
    """Raised when a requested cache entry is missing."""


class CachePutError(DAOError):
    """Raised when writing or updating a cache entry fails."""
