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
    def __init__(self, dicttype, queryset):
        self.dicttype = dicttype
        self.queries = queryset


class APIListHandler(AutoAPIBase):
    def get(self):
        instances = self.queries.get_list()
        instances = json.dumps(instances)
        self.add_to_payload('data', instances)
        return self.render(status_code=200)
    def post(self):
        data = json.loads(self.arguments['data'])
        shield = self.dicttype(**data)
        try:
            shield.validate()
        except ShieldException:
            return self.render(status_code=400)
        self.queries.save_single(shield)
        return self.render(status_code=200)
    #def put(self):
        #replace the entire collection with a new one. This seems dangerous 
    #def delete(self):
        #delete the entire collection. This seems dangerous 
    #def head(self):
        #return metadata about the resource - the headers should be the same as a get requets, but no content body

class APISingleHandler(AutoAPIBase):
    def get(self, item_id):
        instance = self.queries.get_single(item_id)
        instance = json.dumps([instance])
        self.add_to_payload('data', instance)
        return self.render(status_code=200)
    #def post(self):
        # not sure what to do with this - generalized post to item syntax makes me think that:
        # we should check for collection at location.
        # if it's there blow it away with new value, if not assign into collection. Need to read up on this

    #def head(self):
        #return metadata about the resource - the headers should be the same as a get requets, but no content body
    def put(self, item_id):
        data = json.loads(self.arguments['data'])
        shield = self.dicttype(**data)
        try:
            shield.validate()
        except ShieldException:
            return self.render(status_code=400)
        self.queries.save_single(item_id, shield)
        return self.render(status_code=200)
    def delete(self, item_id):
        self.queries.delete(item_id)
        return self.render(status_code=200)
        
    
class APISeveralHandler(AutoAPIBase):
    def get(self, item_ids):
        """ Return a list of resources
        """
        self.ids = item_ids.split(';')
        instances = self.queries.getseveral(self.ids)
        instances = json.dumps(instances)
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
            #have we been given an id that was not requested
            shield = self.dicttype(**item)
            try:
                id = shield[shield._meta['id_field']]
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
        self.queries.save_several(valid)

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
        self.ids = item_ids.split(';')
        self.queries.delete_several(self.ids)
        return self.render(status_code=200)



