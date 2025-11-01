"""Abstract base class for ShortURL data access objects (DAOs).

This class establishes a consistent contract for all ShortURL DAO implementations,
regardless of the underlying storage mechanism (e.g., Redis, DynamoDB, PostgreSQL).

Responsibilities:
    - Provide an interface for inserting and retrieving ShortURLModel objects.
    - Standardize error handling across multiple data store implementations.
    - Enforce a consistent API for use by Lambda functions.

Example:
    Typical usage with a datastore-specific implementation:

        >>> from cloudshortener.models import ShortURLModel
        >>> from cloudshortener.dao import ShortURLRedisDAO

        >>> dao = ShortURLRedisDAO(...)

        >>> short_url = ShortURLModel(
        ...     target="https://example.com/blog/article-123",
        ...     shortcode="a1b2c3",
        ... )
        >>> dao.insert(short_url)

        >>> retrieved = dao.get("a1b2c3")
        >>> print(retrieved.target)
        https://example.com/blog/article-123

        >>> print(retrieved.shortcode)
        a1b2c3

        >>> print(retrieved.expires_at)
        None

TODO:
    - Track and decrement link access quotas per ShortURLModel.
    - Consider whether the DAO should allow manual deletion of entries.
"""

from abc import ABC, abstractmethod

from cloudshortener.models import ShortURLModel


class ShortURLBaseDAO(ABC):
    """Interface for ShortURL data access objects (DAOs).

    Methods:
        insert(short_url: ShortURLModel, **kwargs) -> ShortURLBaseDAO:
            Insert a new ShortURLModel into the data store.
            Raises ShortURLAlreadyExistsError if the short code already exists.
            Raises DataStoreError on connection or write failure.

        get(short_code: str, **kwargs) -> ShortURLModel | None:
            Retrieve a ShortURLModel from the data store by short code.
            Returns None if not found.
            Raises ShortURLNotFoundError if the entry does not exist.
            Raises DataStoreError on connection or read failure.

        count(increment: bool, **kwargs) -> int:
            Return counter from data store.
            Optionally increment counter before retrieving.
            Raises DataStoreError on connection or read failure.

    Subclassing:
        Datastore-specific implementations (e.g., ShortURLRedisDAO or
        ShortURLDynamoDBDAO) must extend this class and implement all
        abstract methods.

    NOTE:
        - Mappings are expected to expire automatically. The DAO does not
          provide an interface to manually delete entries.
    
    TODO:
        - Track and decrement link access quotas per ShortURLModel.
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
    def get(self, shortcode: str, **kwargs) -> ShortURLModel | None:
        """Retrieve a ShortURLModel from the data store by its short code.

        Args:
            short_code (str): 
                The short code of the ShortURLModel to be retrieved.

            **kwargs: 
                Additional keyword arguments, used by data store.

        Returns:
            ShortURLModel | None: The ShortURLModel instance if found, otherwise None.

        Raises:
            ShortURLNotFoundError: 
                If no ShortURLModel with the given short code exists.

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
