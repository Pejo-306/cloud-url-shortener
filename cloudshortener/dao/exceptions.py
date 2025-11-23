"""Exceptions related to Data Access Objects (DAO) operations.

Classes:
    DAOError:
        Generic base class for DAO-related exceptions.

    ShortURLNotFoundError:
        Raised when a ShortURLModel is not found in the data store.

    ShortURLAlreadyExistsError:
        Raised when attempting to insert a ShortURLModel that already exists.

    DataStoreError:
        Raised when there is an error in the data store (e.g., connection issues, time, OOM, etc.).

    UserDoesNotExistError:
        Raised when a user is not found in the data store.

    CacheMissError:
        Raised when a requested cache entry (e.g., AppConfig version) is missing.

    CachePutError:
        Raised when writing or updating a cache entry fails.

Example:
    >>> from cloudshortener.dao.exceptions import CacheMissError
    >>> raise CacheMissError("AppConfig v12 not found in cache.")
    Traceback (most recent call last):
        ...
    cloudshortener.dao.exceptions.CacheMissError: AppConfig v12 not found in cache.
"""


class DAOError(Exception):
    """Generic base class for DAO-related exceptions."""

    pass


class ShortURLNotFoundError(DAOError):
    """Exception raised when a ShortURLModel is not found in the data store."""

    pass


class ShortURLAlreadyExistsError(DAOError):
    """Exception raised when attempting to insert a ShortURLModel that already exists in the data store."""

    pass


class DataStoreError(DAOError):
    """Exception raised when there is an error in the data store.

    e.g. connection issues, timeouts, OOM, etc.
    """

    pass


class UserDoesNotExistError(DAOError):
    """Exception raised when a user is not found in the data store."""

    pass


class CacheMissError(DAOError):
    """Exception raised when a requested cache entry is missing."""

    pass


class CachePutError(DAOError):
    """Exception raised when writing or updating a cache entry fails."""

    pass
