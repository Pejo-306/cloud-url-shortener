from abc import ABC, abstractmethod

from cloudshortener.models import ShortURLModel


class ShortURLBaseDAO(ABC):
    """Interface: Access ShortURL data from the data store.
    
    Methods:
        insert(short_url: ShortURLModel, **kwargs) -> ShortURLBaseDAO:
            Insert a new ShortURLModel into the data store.
            Raises ShortURLAlreadyExistsError if the short code already exists.
            Raises DataStoreError on connection or write failure.

        get(shortcode: str, **kwargs) -> ShortURLModel | None:
            Retrieve a ShortURLModel from the data store by short code.
            Raises ShortURLNotFoundError if the entry does not exist.
            Raises DataStoreError on connection or read failure.

        hit(shortcode: str, **kwargs) -> int:
            Decrement a short URL's monhtly link hit quota.
            Raises ShortURLNotFoundError if the entry does not exist.
            Raises DataStoreError on connection or read failure.

        count(increment: bool, **kwargs) -> int:
            Return counter from data store.
            Optionally increment counter before retrieving.
            Raises DataStoreError on connection or read failure.

    NOTE:
        - Mappings are expected to expire automatically. The DAO does not
          provide an interface to manually delete entries.

    TODO:
        - Consider whether the DAO should allow manual deletion of entries.
    """

    @abstractmethod
    def insert(self, short_url: ShortURLModel, **kwargs) -> 'ShortURLBaseDAO':
        """Insert a new ShortURLModel into the data store.

        Args:
            short_url (ShortURLModel):
                The ShortURLModel instance to be inserted.

            **kwargs:
                Additional keyword arguments, used by data store.

        Returns:
            ShortURLBaseDAO: self (for method chaining)

        Raises:
            ShortURLAlreadyExistsError:
                If a ShortURLModel with the same short code already exists

            DataStoreError:
                If there is an error in the data store.
        """
        pass

    @abstractmethod
    def get(self, shortcode: str, **kwargs) -> ShortURLModel:
        """Retrieve a ShortURLModel from the data store by its short code.

        Args:
            shortcode (str):
                The short code of the ShortURLModel to be retrieved.

            **kwargs:
                Additional keyword arguments, used by data store.

        Returns:
            ShortURLModel: The ShortURLModel instance.

        Raises:
            ShortURLNotFoundError:
                If no ShortURLModel with the given short code exists.

            DataStoreError:
                If there is an error in the data store.
        """
        pass

    @abstractmethod
    def hit(self, shortcode: str, **kwargs) -> int:
        """Decrement a short URL's monhtly link hit quota.

        Args:
            shortcode (str):
                The short code of the ShortURLModel to be retrieved.

            **kwargs:
                Additional keyword arguments, used by data store.

        Return:
            int:
                leftover link hits for this month.

        Raises:
            ShortURLNotFoundError:
                If no short URL with the given short code exists.

            DataStoreError:
                If there is an error in the data store.
        """
        pass

    @abstractmethod
    def count(self, increment: bool = False, **kwargs) -> int:
        """Retrieve the current counter value from the data store.

        Args:
            increment (bool):
                If True, increment the counter by 1 before returning the value.

            **kwargs:
                Additional keyword arguments, used by data store.

        Returns:
            int: The current counter value.

        Raises:
            DataStoreError:
                If there is an error in the data store.
        """
        pass
