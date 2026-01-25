from abc import ABC, abstractmethod


class UserBaseDAO(ABC):
    """Interface: Access user quota data from the data store.

    Methods:
        quota(user_id: str, **kwargs) -> int:
            Retrieve the monthly quota for a user.
            Raises UserDoesNotExistError if the user does not exist.
            Raises DataStoreError on read failure.

        increment_quota(user_id: str, **kwargs) -> int:
            Increment the monthly quota for a user.
            Raises UserDoesNotExistError if the user does not exist.
            Raises DataStoreError on write failure.

    NOTE:
        - Implementations should automatically handle expiration or reset
          of quota values at the start of each month.
    TODO:
        - Consider adding support for administrative overrides.
        - Add support for quota usage analytics.
    """

    @abstractmethod
    def quota(self, user_id: str, **kwargs) -> int:
        """Retrieve the monthly quota for a user.

        NOTE: Implementations of this method guarantee auto-initialization of the user's quota to 0.

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
