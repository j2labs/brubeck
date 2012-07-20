from brubeck.request_handling import FourOhFourException

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

