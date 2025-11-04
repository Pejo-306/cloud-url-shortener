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

Example:
    >>> from cloudshortener.dao.exceptions import ShortURLNotFoundError
    >>> raise ShortURLNotFoundError("Short code 'abc123' not found.")
    Traceback (most recent call last):
        ...
    cloudshortener.dao.exceptions.ShortURLNotFoundError: Short code 'abc123' not found.
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
