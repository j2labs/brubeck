from request_handling import FourOhFourException

class AbstractQueryset(object):
    def __init__(self, db_conn=None, api_id='id'):
        self.db_conn = db_conn
        self.api_id=api_id

    def read(self, ids):
        """Returns a list of items that match ids
        """
        if not ids:
            return self.read_all()
        elif len(ids) == 1:
            return self.read_one(ids[0])
        else:
            return self.read_many(ids)
        

    def read_all(self):
        """Returns a list of objects in the db
        """
        raise NotImplementedError

    def read_one(self, i):
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
        if len(shields) == 1:
            return self.create_one(shields[0])
        else:
            return self.create_many(shields)
    
    def create_one(self, shield):
        raise NotImplementedError

    def create_many(self, shields):
        raise NotImplementedError

    def update(self, shields):
        if len(shields) == 1:
            return self.update_one(shields[0])
        else:
            return self.update_many(shields)
    
    def update_one(self, shield):
        raise NotImplementedError

    def update_many(self, shields):
        raise NotImplementedError

    def destroy(self, item_ids):
        """ Removes items from the datastore
        """
        if len(item_ids) == 1:
            return self.destroy_one(item_ids[0])
        else:
            return self.destroy_many(item_ids)

    def destroy_one(self, i):
        raise NotImplementedError

    def destroy_many(self, ids):
        raise NotImplementedError
    
class DictQueryset(AbstractQueryset):
    def read_all(self):
        return self.db_conn.itervalues()

    def read_one(self, i):
        return self.read_many([i])

    def read_many(self, ids):
        try:
            return [self.db_conn[i] for i in ids]
        except KeyError:
            raise FourOhFourException
                
    def create_one(self, shield):
        return self.create_many([shield])
    
    def create_many(self, shields):
        created, updated = [], []
        for shield in shields:
            if shield.id in self.db_conn:
                updated.append(shield)
            else:
                created.append(shield)
            self.db_conn[str(getattr(shield, self.api_id))] = shield.to_python()
        return created, updated, []
                
    def update_one(self, shield):
        return self.update_many([shield])

    def update_many(self, shields):
        for shield in shields:
            self.db_conn[str(getattr(shield, self.api_id))] = shield.to_python()
        return shields, []
    
    def destroy_one(self, item_id):
        return self.destroy_many([item_id])

    def destroy_many(self, item_ids):
        try:
            for i in item_ids:
                del self.db_conn[i]
        except KeyError:
            raise FourOhFourException
        return item_ids, []
