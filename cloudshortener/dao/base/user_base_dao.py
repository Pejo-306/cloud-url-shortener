"""Abstract base class for user quota data access objects (DAOs).

This interface defines the contract for accessing and managing user quotas
across different storage systems (e.g., Redis, DynamoDB, PostgreSQL).
It standardizes how user quotas are retrieved and incremented for consistent
application-wide usage.

Responsibilities:
    - Provide methods to retrieve and update per-user monthly quotas.
    - Ensure consistent error handling for user and data store operations.
    - Support flexible integration with different data backends.

Example:
    Typical usage with a datastore-specific implementation:

        >>> from cloudshortener.dao import UserRedisDAO
        >>> dao = UserRedisDAO(...)

        >>> quota = dao.quota("user-123")
        >>> print(quota)
        5

        >>> updated = dao.increment_quota("user-123")
        >>> print(updated)
        6

TODO:
    - Add method for resetting or clearing monthly quotas.
    - Consider adding support for administrative overrides.
"""

from abc import ABC, abstractmethod


class UserBaseDAO(ABC):
    """Interface for per-user monthly link generation quota data access objects (DAOs)

    Methods:
        quota(user_id: str, **kwargs) -> int:
            Retrieve the monthly quota for a user.
            Raises UserDoesNotExistError if the user does not exist.
            Raises DataStoreError on read failure.

        increment_quota(user_id: str, **kwargs) -> int:
            Increment the monthly quota for a user.
            Raises UserDoesNotExistError if the user does not exist.
            Raises DataStoreError on write failure.

    Subclassing:
        Concrete implementations (e.g., UserRedisDAO, UserDynamoDBDAO)
        must implement both abstract methods with proper data store logic.

    NOTE:
        - Implementations should automatically handle expiration or reset
          of quota values at the start of each month.
    """

    @abstractmethod
    def quota(self, user_id: str, **kwargs) -> int:
        """Retrieve the monthly quota for a user.

        NOTE: Implementations of this method must guarantee auto-initialization of the user's quota to 0.

        Args:
            user_id (str):
                The user's unique identifier.

            **kwargs:
                Additional keyword arguments, used by data store.

        Returns:
            int:
                The user's monthly quota.

        Raises:
            UserDoesNotExistError:
                If the user does not exist.

            DataStoreError:
                If there is an error in the data store.
        """
        pass

    @abstractmethod
    def increment_quota(self, user_id: str, **kwargs) -> int:
        """Increment the monthly quota for a user.

        Args:
            user_id (str):
                The user's unique identifier.

            **kwargs:
                Additional keyword arguments, used by data store.

        Returns:
            int:
                The user's updated monthly quota.

        Raises:
            UserDoesNotExistError:
                If the user does not exist.

            DataStoreError:
                If there is an error in the data store.
        """
        pass
