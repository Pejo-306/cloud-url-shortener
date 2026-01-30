from cloudshortener.exceptions import CloudShortenerError


class DAOError(CloudShortenerError):
    """Generic base class for DAO-related exceptions."""

    error_code = 'dao:dao_error'


class ShortURLNotFoundError(DAOError):
    """Raised when a ShortURLModel is not found in the data store."""

    error_code = 'dao:short_url_not_found_error'


class ShortURLAlreadyExistsError(DAOError):
    """Raised when inserting a ShortURLModel that already exists in the data store."""

    error_code = 'dao:short_url_already_exists_error'


class DataStoreError(DAOError):
    """Raised when the data store encounters an error.

    Examples include connection issues, timeouts, and out-of-memory failures.
    """

    error_code = 'dao:data_store_error'


class UserDoesNotExistError(DAOError):
    """Raised when a user is not found in the data store."""

    error_code = 'dao:user_does_not_exist_error'


class CacheMissError(DAOError):
    """Raised when a requested cache entry is missing."""

    error_code = 'dao:cache_miss_error'


class CachePutError(DAOError):
    """Raised when writing or updating a cache entry fails."""

    error_code = 'dao:cache_put_error'
