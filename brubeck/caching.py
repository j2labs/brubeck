import os
import time


###
### Sessions are basically caches
###

def generate_session_id():
    """Returns random 32 bit string for cache id
    """
    return os.urandom(32).encode('hex')


###
### Cache storage
###

class BaseCacheStore(object):
    """Ram based cache storage. Essentially uses a dictionary stored in
    the app to store cache id => serialized cache data
    """
    def __init__(self, **kwargs):
        super(BaseCacheStore, self).__init__(**kwargs)
        self._cache_store = dict()

    def save(self, key, data, expire=None):
        """Save the cache data and metadata to the backend storage
        if necessary, as defined by self.dirty == True. On successful
        save set dirty to False.
        """
        cache_item = {
            'key_id': key,
            'data': data,
            'expire': expire,
        }
        self._cache_store[key] = cache_item

    def load(self, key):
        """Load the stored data from storage backend or return None if the
        session was not found. Stale cookies are treated as empty.
        """
        try:
            if key in self._cache_store:
                data = self._cache_store[key]

                # It's an in memory cache, so we must manage
                if data.get('expire', None) and data['expire'] > time.time():
                    return data
            return None
        except:
            return None

    def delete(self, key):
        """Remove all data for the `key` from storage.
        """
        if key in self._cache_store:
            del self._cache_store[key]

    def delete_expired(self):
        """Deletes sessions with timestamps in the past from storage.
        """
        del_keys = list()
        for key, data in self._cache_store.items():
            if data.get('expire', None) and data['expire'] < time.time():
                del_keys.append(key)
        map(self.delete, del_keys)
