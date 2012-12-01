from brubeck.queryset.base import AbstractQueryset
from itertools import imap
import ujson as json
import zlib
try:
    import redis
except ImportError:
    pass

class RedisQueryset(AbstractQueryset):
    """This class uses redis to store the DictShield after 
    calling it's `to_json()` method. Upon reading from the Redis
    store, the object is deserialized using json.loads().

    Redis connection uses the redis-py api located here:
    https://github.com/andymccurdy/redis-py
    """
    # TODO: - catch connection exceptions?
    #       - set Redis EXPIRE and self.expires
    #       - confirm that the correct status is being returned in 
    #         each circumstance
    def __init__(self, compress=False, compress_level=1, **kw):
        """The Redis connection wiil be passed in **kw and is used below
        as self.db_conn.
        """
        super(RedisQueryset, self).__init__(**kw)
        self.compress = compress
        self.compress_level = compress_level
        
    def _setvalue(self, shield):
        if self.compress:
            return zlib.compress(shield.to_json(), self.compress_level)
        return shield.to_json()

    def _readvalue(self, value):
        if self.compress:
            try:
                compressed_value = zlib.decompress(value)
                return json.loads(zlib.decompress(value))
            except Exception as e:
                # value is 0 or None from a Redis return value
                return value
        if value:
            return json.loads(value)
        return None

    def _message_factory(self, fail_status, success_status):
        """A Redis command often returns some value or 0 after the
        operation has returned.
        """
        return lambda x: success_status if x else fail_status

    ### Create Functions

    def create_one(self, shield):
        shield_value = self._setvalue(shield)
        shield_key = str(getattr(shield, self.api_id))        
        result = self.db_conn.hset(self.api_id, shield_key, shield_value)
        if result:
            return (self.MSG_CREATED, shield)
        return (self.MSG_UPDATED, shield)

    def create_many(self, shields):
        message_handler = self._message_factory(self.MSG_UPDATED, self.MSG_CREATED)
        pipe = self.db_conn.pipeline()
        for shield in shields:
            pipe.hset(self.api_id, str(getattr(shield, self.api_id)), self._setvalue(shield))
        results = zip(imap(message_handler, pipe.execute()), shields)
        pipe.reset()
        return results
        
    ### Read Functions

    def read_all(self):
        return [(self.MSG_OK, self._readvalue(datum)) for datum in self.db_conn.hvals(self.api_id)]

    def read_one(self, shield_id):
        result = self.db_conn.hget(self.api_id, shield_id)
        if result:
            return (self.MSG_OK, self._readvalue(result))
        return (self.MSG_FAILED, shield_id)

    def read_many(self, shield_ids):
        message_handler = self._message_factory(self.MSG_FAILED, self.MSG_OK)
        pipe = self.db_conn.pipeline()
        for shield_id in shield_ids:
            pipe.hget(self.api_id, str(shield_id))
        results = pipe.execute()
        pipe.reset()
        return zip(imap(message_handler, results), map(self._readvalue, results))

    ### Update Functions

    def update_one(self, shield):
        shield_key = str(getattr(shield, self.api_id))
        message_handler = self._message_factory(self.MSG_UPDATED, self.MSG_CREATED)
        status = message_handler(self.db_conn.hset(self.api_id, shield_key, self._setvalue(shield)))
        return (status, shield)

    def update_many(self, shields):
        message_handler = self._message_factory(self.MSG_UPDATED, self.MSG_CREATED)
        pipe = self.db_conn.pipeline()
        for shield in shields:
            pipe.hset(self.api_id, str(getattr(shield, self.api_id)), self._setvalue(shield))
        results = pipe.execute()
        pipe.reset()
        return zip(imap(message_handler, results), shields)

    ### Destroy Functions

    def destroy_one(self, shield_id):
        pipe = self.db_conn.pipeline()
        pipe.hget(self.api_id, shield_id)
        pipe.hdel(self.api_id, shield_id)
        result = pipe.execute()
        pipe.reset()
        if result[1]:
            return (self.MSG_UPDATED, self._readvalue(result[0]))
        return self.MSG_NOTFOUND

    def destroy_many(self, ids):
        # TODO: how to handle missing fields, currently returning self.MSG_FAILED
        message_handler = self._message_factory(self.MSG_FAILED, self.MSG_UPDATED)
        pipe = self.db_conn.pipeline()
        for _id in ids:
            pipe.hget(self.api_id, _id)
        values_results = pipe.execute()
        for _id in ids:
            pipe.hdel(self.api_id, _id)
        delete_results = pipe.execute()
        pipe.reset()
        return zip(imap(message_handler, delete_results), map(self._readvalue, values_results))

