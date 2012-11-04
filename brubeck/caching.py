import os
import time
from exceptions import NotImplementedError


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
                if not data.get('expire', None) or data['expire'] > time.time():
                    return data['data']
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

###
### Redis Cache Store
###

class RedisCacheStore(BaseCacheStore):
    """Redis cache using Redis' EXPIRE command to set 
    expiration time. `delete_expired` raises NotImplementedError.
    Pass the Redis connection instance as `db_conn`.

    ##################
    IMPORTANT NOTE:

    This caching store uses a flat namespace for storing keys since
    we cannot set an EXPIRE for a hash `field`. Use different
    Redis databases to keep applications from overwriting 
    keys of other applications.

    ##################
    
    The Redis connection uses the redis-py api located here:
    https://github.com/andymccurdy/redis-py
    """
    
    def __init__(self, redis_connection=None, **kwargs):
        super(RedisCacheStore, self).__init__(**kwargs)
        self._cache_store = redis_connection

    def save(self, key, data, expire=None):
        """expire will be a Unix timestamp
        from time.time() + <value> which is 
        a value in seconds."""

        pipe = self._cache_store.pipeline()
        pipe.set(key, data)
        if expire:
            expire_seconds = expire - time.time()
            assert(expire_seconds > 0)
            pipe.expire(key, int(expire_seconds))
        pipe.execute()
        
    def load(self, key):
        """return the value of `key`. If key
        does not exist or has expired, `hget` will
        return None"""

        return self._cache_store.get(key)
    
    def delete(self, key):
        self._cache_store.delete(key)
        
    def delete_expired(self):
        raise NotImplementedError
