import math
import logging
from dateutil.parser import parse
import re
import uuid


###
### DictShield documents
###

from dictshield.base import BaseField, DictPunch
from dictshield.document import Document
from dictshield.fields import (StringField,
                               BooleanField,
                               URLField,
                               EmailField,
                               LongField,
                               ObjectIdField)

import auth
from timekeeping import curtime, MillisecondField


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
    
class UserProfile(Document):
    """The basic things a user profile tends to carry. Isolated in separate
    class to keep separate from private data.
    """
    # ownable
    owner = ObjectIdField(required=True)
    username = StringField(max_length=30, required=True)

    # streamable
    created_at = MillisecondField()
    updated_at = MillisecondField()

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


