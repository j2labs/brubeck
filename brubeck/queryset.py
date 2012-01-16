from request_handling import FourOhFourException


STATUS_OK = 'OK'
STATUS_UPDATED = 'Updated'
STATUS_CREATED = 'Created'
STATUS_NOTFOUND = 'Not Found'
STATUS_FAILED = 'Failed'

    
class AbstractQueryset(object):
    
    def __init__(self, db_conn=None, api_id='id'):
        self.db_conn = db_conn
        self.api_id = api_id

    def read(self, ids):
        """Returns a list of items that match ids
        """
        if not ids:
            return self.read_all()
        elif isinstance(ids, list):
            return self.read_many(ids)
        else:
            return self.read_one(ids)

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

    def create(self, shields):
        """Commits a list of new shields to the database
        """
        if isinstance(shields, list):
            return self.create_many(shields)
        else:
            return self.create_one(shields)

    def create_one(self, shield):
        raise NotImplementedError

    def create_many(self, shields):
        raise NotImplementedError

    def update(self, shields):
        if isinstance(shields, list):
            return self.update_many(shields)
        else:
            return self.update_one(shields)

    def update_one(self, shield):
        raise NotImplementedError

    def update_many(self, shields):
        raise NotImplementedError

    def destroy(self, item_ids):
        """ Removes items from the datastore
        """
        if isinstance(item_ids, list):
            return self.destroy_many(item_ids)
        else:
            return self.destroy_one(item_ids)

    def destroy_one(self, iid):
        raise NotImplementedError

    def destroy_many(self, ids):
        raise NotImplementedError


class DictQueryset(AbstractQueryset):
    def __init__(self, **kw):
        """Set the db_conn to a dictionary.
        """
        super(DictQueryset, self).__init__(db_conn=dict(), **kw)
    
    def read_all(self):
        return [(STATUS_OK, datum) for datum in self.db_conn.values()]

    def read_one(self, iid):
        if iid in self.db_conn:
            return (STATUS_UPDATED, self.db_conn[iid])
        else:
            return (STATUS_FAILED, self.db_conn[iid])

    def read_many(self, ids):
        try:
            return [self.read_one(iid) for iid in ids]
        except KeyError:
            raise FourOhFourException

    def create_one(self, shield):
        if shield.id in self.db_conn:
            status = STATUS_UPDATED
        else:
            status = STATUS_CREATED

        shield_key = str(getattr(shield, self.api_id))
        self.db_conn[shield_key] = shield.to_python()
        return (status, shield)

    def create_many(self, shields):
        statuses = [self.create_one(shield) for shield in shields]
        return statuses

    def update_one(self, shield):
        shield_key = str(getattr(shield, self.api_id))
        self.db_conn[shield_key] = shield.to_python()
        return (STATUS_UPDATED, shield)

    def update_many(self, shields):
        statuses = [self.update_one(shield) for shield in shields]
        return statuses

    def destroy_one(self, item_id):
        try:
            shield = self.db_conn[item_id]
            del self.db_conn[item_id]
        except KeyError:
            raise FourOhFourException
        return (STATUS_UPDATED, shield)

    def destroy_many(self, ids):
        statuses = [self.destroy_one(iid) for iid in ids]
        return statuses
