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

import auth
from timekeeping import curtime
from datamosh import OwnedModelMixin, StreamedModelMixin


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
    ## ownable # Provided by OwnedModelMixin now. includes a name changes
    #owner = ObjectIdField(required=True) # owner_id
    #username = StringField(max_length=30, required=True) # owner_username

    ## streamable # provided by StreamedModelMixin now
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
        'owner',
    ]

    def __init__(self, *args, **kwargs):
        super(UserProfile, self).__init__(*args, **kwargs)

    def __unicode__(self):
        return u'%s' % (self.name)




###
### API mixin
###


class APIableMixin(object):
    def __init__(self, queryset=None, dicttype=None):
        pass
        #create class with self as model  and queryset to pull them
        #register new class to routes
        #register itself with brubeck's manafest

class AutoAPIBase(JSONMessageHandler):
    def __init__(self, dicttype, queryset, *args, **kwargs):
        self.dicttype = dicttype
        self.queries = queryset
        super(AutoAPIBase, self).__init__(*args, **kwargs)


    def add_single(self, item_id=None):
        """Adds a single item to the database - the item should be represented as a object
        inside a single item list,  in an object with the "data" key.
        e.g.
        { 'data' : [
                    {
                     'mysamplekey1':somesamplevalue,
                     'mysamplekey2':somesamplevalue,
                    }
                   ]
        }

        This keeps the interface constant if you're passing a single item or a list of items.
        We only want to deal with sequences!
        """
        
        #load data from postbody
        data = json.loads(self.arguments['data'])
        #ensure it's good data
        shield = self.dicttype(**data)
        shield.validate()
        #serialze and persist the data
        shield = self.queries.save_single(shield, item_id)
        #return the local representation of the shield
        self.add_to_payload('data', json.dumps([shield.to_json()]))



class APIListHandler(AutoAPIBase):
    def get(self):
        """Returns a jsonifyed list of objects in the db.
        """
        #TODO:Figure out how we want to pagify this or somehow break it down from a single monster rv
        instances = self.queries.get_list()
        instances = json.dumps([instance.to_json() for instance in instances])
        self.add_to_payload('data', instances)
        return self.render(status_code=200)

    def post(self):
        """Adds a single _new_ item to the database and returns a representation of it
        """
        try:
            self.add_single()
        except ShieldException:
            return self.render(status_code=400)

        return self.render(status_code=201)

    #def put(self):
        #replace the entire collection with a new one. This seems dangerous 
    #def delete(self):
        #delete the entire collection. This seems dangerous 
    #def head(self):
        #return metadata about the resource - the headers should be the same as a get requets, but no content body

class APISingleHandler(AutoAPIBase):
    def get(self, item_id):
        """Pull out the representation of an item in the db
        """
        try:
            instance = self.queries.get_single(item_id)
        except KeyError:
            return self.render(status_code=404)
        self.add_to_payload('data', json.dumps([instance.to_json()]))
        return self.render(status_code=200)

    def put(self, item_id):
        """Updates an item in the db
        """
        try:
            self.add_single(item_id)
        except ShieldException:
            return self.render(status_code=400)
        except KeyError:
            return self.render(status_code=404)            

        return self.render(status_code=200)

    def delete(self, item_id):
        """ Deletes an item in the db
        """
        try:
            self.queries.delete_single(item_id)
        except KeyError:
            return self.render(status_code=404)
        return self.render(status_code=200)


    #def post(self):
        # not sure what to do with this - generalized post to item syntax makes me think that:
        # we should check for collection at location.
        # if it's there blow it away with new value, if not assign into collection. Need to read up on this

    #def head(self):
        #return metadata about the resource - the headers should be the same as a get requets, but no content body

class APISeveralHandler(AutoAPIBase):
    def get(self, item_ids):
        """ Return a list of resources
        """
        self.ids = item_ids.split(';')
        try:
            instances = self.queries.get_several(self.ids)
        except KeyError:
            #TODO: return representation of which items were found and which ones weren't
            return self.render(status_code=404)

        instances = json.dumps([instance.to_json() for instance in instances])
        self.add_to_payload('data', instances)
        return self.render(status_code=200)

    #def head(self):
        #return metadata about the resource - the headers should be the same as a get requets, but no content body
    def put(self, item_ids):
        """Updates a list of items in place. Used as a cheat to combine what could be several requests into a single one
        """
        self.ids = item_ids.split(';')
        valid, invalid = [], []
        data = json.loads(self.arguments['data'])
        for item in data:
            shield = self.dicttype(**item)
            try:
                #have we been given an id that was not requested? Consume the ids on self to find out!
                obj_id = shield.id
                self.ids.remove(id)
            except ValueError:
                #item included in data that shouldn't have been. Bail.
                return self.render(status_code=400)
            try:
                #did we get good data
                shield.validate()
                valid.append(item)
            except ShieldException:
                invalid.append(item)

        #the request asked for more resources than they actually needed. Enforce a good request!
        if self.ids:
            return self.render(status_code=400)
        #commit this to the db
        try:
            self.queries.save_several(valid)
        except KeyError:
            #TODO: return reprentation of which ones were successfully updated
            return self.render(status_code=404)

        if not invalid:
            #we're all good, so return the all clear
            return self.render(status_code=200)

        #some failed - return a list of which ones worked
        else:
            data = []
            [data.append({'id': id, 'status' : '400'}) for id in invalid]
            [data.append({'id': id, 'status' : '200'}) for id in valid]
            data = json.dumps(data)
            self.add_to_payload('data', data)
            return self.render(status_code=400)
            
    def delete(self, item_ids):
        """ Deletes a list of items. this is really a cheat for a bunch of DELETE requests to foo/xxx
        """
        ids = item_ids.split(';')
        try:
            self.queries.delete_several(ids)
        except KeyError:
            return self.render(status_code=404)
        return self.render(status_code=200)


class AbstractQueryset(object):
    def __init__(self, db_conn=None):
        self.db_conn = db_conn


    ###
    ### - Common API functions
    ###

    def save_single(self, shield, object_id=None):
        """Takes a single dictshield and commits it to the db
        Optional argument object_id  - if included, this is an update, and if missing this is a create
        """
        if object_id:
            return self.update_single(shield, object_id)
        else:
            return self.create_single(shield)

    ###
    ### -  List API functions
    ###

    def create_single(self, shield):
        raise NotImplementedError
    
    def get_list(self):
        """Returns a list of objects in the db
        """
        raise NotImplementedError

    ###
    ### - Single API functions
    ###


    def update_single(self, shield, object_id):
        raise NotImplementedError
    
    def get_single(self, item_id):
        """ Pulls a single item out of the db and returns it
        """
        raise NotImplementedError


    def delete_single(self, item_id):
        """ Removes a single item from the db
        """
        raise NotImplementedError

    
    ###
    ### - Several Item API functions
    ###
        
    def save_several(self, shields):
        """Takes a list of dictshield objects and serializes them to the db
        """
        raise NotImplementedError

    def get_several(self, ids):
        """Takes a list of ids, and returns a list of objects matching those ids
        """
        raise NotImplementedError

    def delete_several(self, ids):
        """Takes a list of ids and removes the items matching those ids from the database
        """
        raise NotImplementedError
    


def DictQueryset(AbstractQueryset):
    def get_list(self):
        return self.db_conn.iter_values()

    def create_single(self, shield):
        self.db_conn[id] = shield.to_python()
        return self.db_conn[id]
        
    def update_single(self, shield, item_id):
        self.db_conn[item_id] = shield.to_python()
        return self.db_conn[item_id]

    def get_single(self, item_id):
        return self.db_conn[item_id]

    def delete_single(self, item_id):
        del self.db_conn[item_id]

    def save_several(self, shields):
        items = {}
        for shield in shields:
            items[shield.id] = shield.to_python()
        self.db_conn.update(items)
        return items

    def get_several(self, ids):
        return [self.db_conn[idz] for idz in ids]

    def delete_several(self, ids):
        for idz in ids:
            del self.db_conn[id]
