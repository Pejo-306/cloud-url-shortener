import redis


type DataStoreType = str  # redis, postgresql, etc.
type DataStoreClient = redis.Redis


class DataStores:
    def __init__(self, data_stores: dict[DataStoreType, DataStoreClient]):
        self._redis = data_stores.get('redis')

    @property
    def redis(self) -> redis.Redis | None:
        return self._redis
