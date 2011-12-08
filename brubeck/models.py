from itertools import chain
import re
import json
###
### DictShield documents
###

from dictshield.document import Document
from dictshield.base import ShieldException
from dictshield.fields import (StringField,
                               BooleanField,
                               URLField,
                               EmailField,
                               LongField,
                               )
from brubeck.request_handling import JSONMessageHandler
from dictshield.fields.mongo import ObjectIdField

import auth
from timekeeping import curtime
from datamosh import OwnedModelMixin, StreamedModelMixin


MULTIPLE_ITEM_SEP = ','

###
### User Document
###

class User(Document):
    """Bare minimum to have the concept of a User.
    """
    username = StringField(max_length=30, required=True)
    password = StringField(max_length=128)

    is_active = BooleanField(default=False)
    last_login = LongField(default=curtime)
    date_joined = LongField(default=curtime)

    _private_fields = [
        'password', 'is_active',
    ]

    username_regex = re.compile('^[A-Za-z0-9._]+$')
    username_min_length = 2

    def __unicode__(self):
        return u'%s' % (self.username)

    def set_password(self, raw_passwd):
        """Generates bcrypt hash and salt for storing a user's password. With
        bcrypt, the salt is kind of redundant, but this format stays friendly
        to other algorithms.
        """
        (algorithm, salt, digest) = auth.gen_hexdigest(raw_passwd)
        self.password = auth.build_passwd_line(algorithm, salt, digest)

    def check_password(self, raw_password):
        """Compares raw_password to password stored for user. Updates
        self.last_login on success.
        """
        algorithm, salt, hash = auth.split_passwd_line(self.password)
        (_, _, user_hash) = auth.gen_hexdigest(raw_password,
                                               algorithm=algorithm, salt=salt)
        if hash == user_hash:
            self.last_login = curtime()
            return True
        else:
            return False

    @classmethod
    def create_user(cls, username, password, email=str()):
        """Creates a user document with given username and password
        and saves it.

        Validation occurs only for email argument. It makes no assumptions
        about password format.
        """
        now = curtime()

        username = username.lower()
        email = email.strip()
        email = email.lower()

        # Username must pass valid character range check.
        if not cls.username_regex.match(username):
            warning = 'Username failed character validation - username_regex'
            raise ValueError(warning)
        
        # Caller should handle validation exceptions
        cls.validate_class_partial(dict(email=email))

        user = cls(username=username, email=email, date_joined=now)
        user.set_password(password)
        return user


###
### UserProfile
###
    
class UserProfile(Document, OwnedModelMixin, StreamedModelMixin):
    """The basic things a user profile tends to carry. Isolated in separate
    class to keep separate from private data.
    """
    # Provided by OwnedModelMixin
    #owner_id = ObjectIdField(required=True)
    #owner_username = StringField(max_length=30, required=True)

    # streamable # provided by StreamedModelMixin now
    #created_at = MillisecondField()
    #updated_at = MillisecondField()

    # identity info
    name = StringField(max_length=255)
    email = EmailField(max_length=100)
    website = URLField(max_length=255)
    bio = StringField(max_length=100)
    location_text = StringField(max_length=100)
    avatar_url = URLField(max_length=255)

    _private_fields = [
        'owner_id',
    ]

    def __init__(self, *args, **kwargs):
        super(UserProfile, self).__init__(*args, **kwargs)

    def __unicode__(self):
        return u'%s' % (self.name)




###
### API mixin
###

class FourOhFourException(Exception):
    pass

    
class AbstractQueryset(object):
    def __init__(self, db_conn=None):
        self.db_conn = db_conn


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
    
class AutoAPIBase(JSONMessageHandler):
    model = None
    queries = AbstractQueryset()

    ###
    ### configuring input and output formats
    ###

    def _get_shields_from_postbody(self):
        """ Describes how our incoming data looks
        """
        items = json.loads(self.get_argument('data'))
        shields = [self.model(**item) for item in items]
        return shields


    def _create_response(self, updated, failed=[], created=[]):
        """Passed a list of shields and the state they're in, and creates a response
        """
        status = []
        status.extend([{'status':201, 'id':str(shield.id), 'href':self.uri_for_shield(shield)} for shield in created])
        status.extend([{'status':200, 'id':str(shield.id), 'href':self.uri_for_shield(shield)} for shield in updated])
        status.extend([{'status':400, 'id':str(shield.id), 'href':self.uri_for_shield(shield)} for shield in failed])

        self.add_to_payload('data', [shield.to_json(encode=False) for shield in chain(created, updated, failed)])
        self.add_to_payload('multistatus', status)

        status_code = self._get_status_code(updated, failed, created)
        
        return self.render(status_code=status_code)


    ###
    ### -General Validation and private computation
    ###

    def _get_status_code(self, updated, failed, created=[]):
        """Creates the status code we should be returning based on our successes and failures
        """
        kinds = reduce(lambda old, new: old + 1 if new else old, [created, updated, failed], 0)
        if kinds > 1:
            status_code = 207 #multistatus!
        else:
            if failed:
                status_code = 400
            elif created:
                status_code = 201
            else:
                status_code = 200
        return status_code

    def _pre_alter_validation(self):
        """ Creates the shield objcts and validates that they're in the right format
        if they're not, adds the error list to the payload
        """
        shields = self._get_shields_from_postbody()
        invalid = self._validate(shields)

        if invalid:
            errors = [{'status':422,
                       'id':shield.id,
                       'error':error,
                       'href':self.uri_for_shield(shield)
                       } for shield, error in invalid]
            self.add_to_payload('multistatus', json.dumps(errors))
        return shields, invalid

    def _validate(self, shields):
        """ seperates the list of items into valid and invalid shields
        """
        invalid = []
        for shield in shields:
            try:
                shield.validate()
            except ShieldException, e:
                invalid.append((shield, e))
        return invalid

    def url_matches_body(self, item_ids, shields):
        """ We want to make sure that if the request asks for a specific few resources,
        Those resources and only those resources are in the body
        """
        if not item_ids: return True 
        for item_id, shield in zip(item_ids, shields):
            if item_id != str(shield.id): # enforce a good request
                return False
        return True

    def uri_for_shield(self, shield):
        return str(shield.id)

    ###
    ### HTTP methods
    ###
    
    def get(self, item_ids=""):
        """Handles read - either with a filter (item_ids) or a total list
        """
        try:
            shields = self.read([v for v in item_ids.split(MULTIPLE_ITEM_SEP) if v])
        except FourOhFourException:
            return self.render(status_code=404)
        return self._create_response(shields)


    def post(self, item_ids=""):
        """ Handles create if item_ids is missing, else
        updates the items.

        Items should be represented as objects 
        inside a list, pegged to the global object  -  the global object name defaults to data but can be changed
        by overriding the _get_shields_from_postbody method
        e.g.
        { 'data' : [
                    {
                     'mysamplekey1':somesamplevalue,
                     'mysamplekey2':somesamplevalue,
                    },
                    {
                     'mysamplekey1':somesamplevalue,
                     'mysamplekey2':somesamplevalue,
                    },
                   ]
        }

        This keeps the interface constant if you're passing a single item or a list of items.
        We only want to deal with sequences!
        """
        shields, invalid = self._pre_alter_validation()
        if invalid:
            return self.render(status_code=400)
        if item_ids == "":

            created, updated, failed = self.create(shields)
            return self._create_response(updated, failed, created)
        else:
            if not self.url_matches_body(item_ids.split(MULTIPLE_ITEM_SEP), shields):
                #TODO: add error message so client knows why the request failed
                return self.render(status_code=400)

            successes, failures = self.update(shields)

            return self._create_response(successes, failures)
            
    def put(self, item_ids):
        """ Handles update for 1 or many items.
        Take the postbody and convert it into a list of shields, and then confirm that matches
        the item ids passed in.

                Items should be represented as a object
        inside a list,  in an object with the "data" key.
        e.g.
        { 'data' : [
                    {
                     'mysamplekey1':somesamplevalue,
                     'mysamplekey2':somesamplevalue,
                    },
                    {
                     'mysamplekey1':somesamplevalue,
                     'mysamplekey2':somesamplevalue,
                    },
                   ]
        }

        This keeps the interface constant if you're passing a single item or a list of items.
        We only want to deal with sequences!
        """
        shields, invalid = self._pre_alter_validation()
        if invalid:
            return self.render(status_code=400)
        if not self.url_matches_body(item_ids.split(MULTIPLE_ITEM_SEP), shields):
            #TODO: add error message so client knows why the request failed
            return self.render(status_code=400)
        successes, failures = self.update(shields)
        return self._create_response(successes, failures)

    def delete(self, item_ids):
        """ Handles delete for 1 or many items. Since this doesn't take a postbody, and just
        Item ids, pass those on directly to destroy
        """
        item_ids = item_ids.split(MULTIPLE_ITEM_SEP)
        try:
            successes, failures = self.destroy(item_ids)
        except FourOhFourException:
            return self.render(status_code=404)
        status_code = self._get_status_code(successes, failures)

        status = []
        status.extend([{'status':200, 'id':i} for i in successes])
        status.extend([{'status':400, 'id':i} for i in failures])
        self.add_to_payload('multistatus', json.dumps(status))

        return self.render(status_code=status_code)

    ###
    ### -CRUD operations
    ### 

    def read(self, include):
        """Returns a list of shields in the db.
        takes a list of object ids to include - if that's empty then include everything
        """
        #TODO:Figure out how we want to pagify this or somehow break it down from a single monster rv
        list_of_data = self.queries.read(include)
        if include and not list_of_data:
            raise FourOhFourException
        return [self.model(**data) for data in list_of_data]

    def create(self, shields):
        """Ment for adding items to the database and returns a list of successful creations, updates and failures
        Such that: 
        created, updated, failed = self.create(shields)
        """
        return self.queries.create(shields) #lists of status and post-save representation

    def destroy(self, item_ids):
        """ Removes the passed ids from the datastore and returns a list of success and failures
        Such that:
        success, failure = self.destroy(item_ids)
        """
        return self.queries.destroy(item_ids)

    def update(self, shields):
        """ updates the passed sheilds in the datastore and returns a list of success and failures
        Such that:
        successes, failures = self.update(shields)
        """
        return self.queries.update(shields)

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
            self.db_conn[str(shield.id)] = shield.to_python()
        return created, updated, []
                
    def update_one(self, shield):
        return self.update_many([shield])

    def update_many(self, shields):
        for shield in shields:
            self.db_conn[str(shield.id)] = shield.to_python()
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
