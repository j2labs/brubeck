from request_handling import FourOhFourException
from itertools import imap
import zlib

class AbstractQueryset(object):
    """The design of the `AbstractQueryset` attempts to map RESTful calls
    directly to CRUD calls. It also attempts to be compatible with a single
    item of a list of items, handling multiple statuses gracefully if
    necessary.

    The querysets then must allow for calls to perform typical CRUD operations
    on individual items or a list of items.

    By nature of being dependent on complete data models or ids, the system
    suggests users follow a key-value methodology. Brubeck believes this is
    what we scale into over time and should just build to this model from the
    start.

    Implementing the details of particular databases is then to implement the
    `create_one`, `create_many`, ..., for all the CRUD operations. MySQL,
    Mongo, Redis, etc should be easy to implement while providing everything
    necessary for a proper REST API.
    """

    MSG_OK = 'OK'
    MSG_UPDATED = 'Updated'
    MSG_CREATED = 'Created'
    MSG_NOTFOUND = 'Not Found'
    MSG_FAILED = 'Failed'
    MSG_EXISTS = 'Exists'

    def __init__(self, db_conn=None, api_id='id'):
        self.db_conn = db_conn
        self.api_id = api_id

    ###
    ### CRUD Operations
    ###

    ### Section TODO:
    ### * Pagination
    ### * Hook in authentication
    ### * Key filtering (owner / public)
    ### * Make model instantiation an option

    def create(self, shields):
        """Commits a list of new shields to the database
        """
        if isinstance(shields, list):
            return self.create_many(shields)
        else:
            return self.create_one(shields)

    def read(self, ids):
        """Returns a list of items that match ids
        """
        if not ids:
            return self.read_all()
        elif isinstance(ids, list):
            return self.read_many(ids)
        else:
            return self.read_one(ids)

    def update(self, shields):
        if isinstance(shields, list):
            return self.update_many(shields)
        else:
            return self.update_one(shields)

    def destroy(self, item_ids):
        """ Removes items from the datastore
        """
        if isinstance(item_ids, list):
            return self.destroy_many(item_ids)
        else:
            return self.destroy_one(item_ids)

    ###
    ### CRUD Implementations
    ###

    ### Create Functions

    def create_one(self, shield):
        raise NotImplementedError

    def create_many(self, shields):
        raise NotImplementedError

    ### Read Functions

    def read_all(self):
        """Returns a list of objects in the db
        """
        raise NotImplementedError

    def read_one(self, iid):
        """Returns a single item from the db
        """
        raise NotImplementedError

    def read_many(self, ids):
        """Returns a list of objects matching ids from the db
        """
        raise NotImplementedError

    ### Update Functions

    def update_one(self, shield):
        raise NotImplementedError

    def update_many(self, shields):
        raise NotImplementedError

    ### Destroy Functions

    def destroy_one(self, iid):
        raise NotImplementedError

    def destroy_many(self, ids):
        raise NotImplementedError


class DictQueryset(AbstractQueryset):
    """This class exists as an example of how one could implement a Queryset.
    This model is an in-memory dictionary and uses the model's id as the key.

    The data stored is the result of calling model's `to_python()` function.
    """
    def __init__(self, **kw):
        """Set the db_conn to a dictionary.
        """
        super(DictQueryset, self).__init__(db_conn=dict(), **kw)

    ### Create Functions

    def create_one(self, shield):
        if shield.id in self.db_conn:
            status = self.MSG_UPDATED
        else:
            status = self.MSG_CREATED

        shield_key = str(getattr(shield, self.api_id))
        self.db_conn[shield_key] = shield.to_python()
        return (status, shield)

    def create_many(self, shields):
        statuses = [self.create_one(shield) for shield in shields]
        return statuses

    ### Read Functions

    def read_all(self):
        return [(self.MSG_OK, datum) for datum in self.db_conn.values()]


    def read_one(self, iid):
        iid = str(iid)  # TODO Should be cleaner
        if iid in self.db_conn:
            return (self.MSG_OK, self.db_conn[iid])
        else:
            return (self.MSG_FAILED, iid)

    def read_many(self, ids):
        return [self.read_one(iid) for iid in ids]

    ### Update Functions
    def update_one(self, shield):
        shield_key = str(getattr(shield, self.api_id))
        self.db_conn[shield_key] = shield.to_python()
        return (self.MSG_UPDATED, shield)

    def update_many(self, shields):
        statuses = [self.update_one(shield) for shield in shields]
        return statuses

    ### Destroy Functions

    def destroy_one(self, item_id):
        try:
            datum = self.db_conn[item_id]
            del self.db_conn[item_id]
        except KeyError:
            raise FourOhFourException
        return (self.MSG_UPDATED, datum)

    def destroy_many(self, ids):
        statuses = [self.destroy_one(iid) for iid in ids]
        return statuses

class RedisQueryset(AbstractQueryset):
    """This class uses redis to store the DictShield
    This model is an in-memory dictionary and uses the model's id as the key.

    The data stored is the result of calling model's `to_python()` function.

    Redis connection uses the redis-py api located here:
    https://github.com/andymccurdy/redis-py

    All shield ids are assumed to be strings
    """
    # TODO: - catch connection exceptions?
    #       - set Redis EXPIRE and self.expires
    #       - are shield ids always strings or numbers or either?
    #         - should getattr(shield, self.api_id) be used as the Redis hash key?
    #      
    def __init__(self, compress=False, compress_level=1):
        """The Redis connection wiil be passed in **kw and is used below
        as self.db_conn.
        """
        super(AbstractQueryset, self).__init__(**kw)
        self.compress = compress
        self.compress_level = compress_level

    def _setvalue(self, shield):
        if self.compress:
            return zlib.compress(shield.to_json(), self.compress_level)
        return shield.to_json()

    def _readvalue(self, value):
        if self.compress:
            return zlib.decompress(value)
        return value

    def _message_factory(self, fail_status, success_status):
        """A Redis value returns 1 or 0 upon success or failure, respectively
        """
        return lambda x: success_status if x else fail_status

    ### Create Functions

    def create_one(self, shield):
        shield_value = self._value(shield)
        
        if self.db_conn.hexists(self.api_id, shield.id):
            return (self.MSG_EXISTS, shield)

        self.db_conn.hset(self.api_id, shield.id, shield_value)
        return (self.MSG_CREATED, shield)

    def create_many(self, shields):
        message_handler = self._message_factory(self.MSG_EXISTS, self.MSG_CREATED)
        pipe = self.db_conn.pipeline()
        [pipe.hsetnx(self.api_id, shield.id, self._value(shield)) for shield in shields]
        results = zip(imap(message_handler, pipe.execute()), shields)
        pipe.reset()
        return results

    ### Read Functions

    def read_all(self):
        return [(self.MSG_OK, datum) for datum in self.db_conn.hgetall(self.api_id)]

    def read_one(self, shield_id):
        if self.db_conn.hexists(self.api_id, shield_id):
            return (self.MSG_OK, _readvalue(self.db_conn.hget(self.api_id, shield_id)))
        else:
            return (self.MSG_NOTFOUND, shield_id)

    def read_many(self, shield_ids):
        message_handler = self._message_factory(self.MSG_NOTFOUND, self.MSG_OK)
        pipe = self.db_conn.pipeline()
        [pipe.hget(self.api_id, shield_id) for shield_id in shield_ids]
        results = pipe.execute()
        pipe.reset()
        return zip(imap(message_handler, results), map(_readvalue, results))


    ### Update Functions
    def update_one(self, shield):
        message_handler = _message_factory(self.MSG_NOTFOUND, self.MSG_UPDATED)
        return (message_handler(self.db_conn.hsetnx(self.api_id, shield.id)), shield)

    def update_many(self, shields):
        message_handler = _message_factory(self.MSG_NOTFOUND, self.MSG_UPDATED)
        pipe = self.db_conn.pipeline()
        [pipe.hsetnx(self.api_id, shield.id, _value(shield)) for shield in shields]
        results = pipe.execute()
        pipe.reset()
        return imap(message_handler, results)

    ### Destroy Functions

    def destroy_one(self, shield_id):
        if self.db_conn.hdel(self.api_id, shield_id):
            return self.MSG_OK
        return self.MSG_NOTFOUND

    def destroy_many(self, ids):
        message_handler = _message_factory(self.MSG_NOTFOUND, self.MSG_OK)
        pipe = self.db_conn.pipeline()
        [pipe.hdel(self.api_id, _id) for _id in ids]
        results = pipe.execute()
        pipe.reset()
        return imap(message_handler, results)

