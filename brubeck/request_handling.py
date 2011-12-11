#!/usr/bin/env python


"""Brubeck is a coroutine oriented zmq message handling framework. I learn by
doing and this code base represents where my mind has wandered with regard to
concurrency.

If you are building a message handling system you should import this class
before anything else to guarantee the eventlet code is run first.

See github.com/j2labs/brubeck for more information.
"""

### Attempt to setup gevent
try:
    from gevent import monkey
    monkey.patch_all()
    from gevent import pool
    from gevent_zeromq import zmq

    coro_pool = pool.Pool
    def coro_spawn(function, app, message, *a, **kw):
        app.pool.spawn(function, app, message, *a, **kw)

    CORO_LIBRARY = 'gevent'

### Fallback to eventlet
except ImportError:
    try:
        import eventlet
        eventlet.patcher.monkey_patch(all=True)
        from eventlet.green import zmq

        coro_pool = eventlet.GreenPool
        def coro_spawn(function, app, message, *a, **kw):
            app.pool.spawn_n(function, app, message, *a, **kw)

        CORO_LIBRARY = 'eventlet'

    except ImportError: ### eventlet or gevent is required.
        raise EnvironmentError('Y U NO INSTALL CONCURRENCY?!')


from . import version

import re
import time
import logging
import inspect
import Cookie
import base64
import hmac
import cPickle as pickle
from itertools import chain

from mongrel2 import Mongrel2Connection, to_bytes, to_unicode
from dictshield.base import ShieldException



import ujson as json

###
### Common helpers
###
HTTP_METHODS = ['get', 'post', 'put', 'delete', 'head', 'options', 'trace', 'connect']

class FourOhFourException(Exception):
    pass


HTTP_FORMAT = "HTTP/1.1 %(code)s %(status)s\r\n%(headers)s\r\n\r\n%(body)s"
def http_response(body, code, status, headers):
    """Renders arguments into an HTTP response.
    """
    payload = {'code': code, 'status': status, 'body': body}
    content_length = 0
    if body is not None:
        content_length = len(to_bytes(body))
    headers['Content-Length'] = content_length
    payload['headers'] = "\r\n".join('%s: %s' % (k,v) for k,v in
                                     headers.items())

    return HTTP_FORMAT % payload

def _lscmp(a, b):
    """Compares two strings in a cryptographically safe way
    """
    return not sum(0 if x==y else 1 for x, y in zip(a, b)) and len(a) == len(b)


###
### Message handling coroutines
###

def route_message(application, message):
    """This is the first of the three coroutines called. It looks at the
    message, determines which handler will be used to process it, and
    spawns a coroutine to run that handler.

    The application is responsible for handling misconfigured routes.
    """
    handler = application.route_message(message)
    coro_spawn(request_handler, application, message, handler)

def request_handler(application, message, handler):
    """Coroutine for handling the request itself. It simply returns the request
    path in reverse for now.
    """
    if callable(handler):
        response = handler()
        coro_spawn(result_handler, application, message, response)
    
def result_handler(application, message, response):
    """The request has been processed and this is called to do any post
    processing and then send the data back to mongrel2.
    """
    application.m2conn.reply(message, response)


###
### Me not *take* cookies, me *eat* the cookies.
###

def cookie_encode(data, key):
    """Encode and sign a pickle-able object. Return a (byte) string
    """
    msg = base64.b64encode(pickle.dumps(data, -1))
    sig = base64.b64encode(hmac.new(key, msg).digest())
    return to_bytes('!') + sig + to_bytes('?') + msg

def cookie_decode(data, key):
    ''' Verify and decode an encoded string. Return an object or None.'''
    data = to_bytes(data)
    if cookie_is_encoded(data):
        sig, msg = data.split(to_bytes('?'), 1)
        if _lscmp(sig[1:], base64.b64encode(hmac.new(key, msg).digest())):
            return pickle.loads(base64.b64decode(msg))
    return None

def cookie_is_encoded(data):
    ''' Return True if the argument looks like a encoded cookie.'''
    return bool(data.startswith(to_bytes('!')) and to_bytes('?') in data)


###
### Message handling
###

class MessageHandler(object):
    """The base class for request handling. It's functionality consists
    primarily of a payload system and a way to store some state for
    the duration of processing the message.

    Mixins are provided in Brubeck's modules for extending these handlers.
    Mixins provide a simple way to add functions to a MessageHandler that are
    unique to the message our handler is designed for. Mix in logic as you
    realize you need it. Or rip it out. Keep your handlers lean.

    Two callbacks are offered for state preparation.

    The `initialize` function allows users to add steps to object
    initialization. A mixin, however, should never use this. You could hook
    the request handler up to a database connection pool, for example.

    The `prepare` function is called just before any decorators are called.
    The idea here is to give Mixin creators a chance to build decorators that
    depend on post-initialization processing to have taken place. You could use
    that database connection we created in `initialize` to check the username
    and password from a user.
    """
    _STATUS_CODE = 'status_code'
    _STATUS_MSG = 'status_msg'
    _TIMESTAMP = 'timestamp'
    _DEFAULT_STATUS = -1 # default to error, earn success
    _SUCCESS_CODE = 0
    _AUTH_FAILURE = -2
    _SERVER_ERROR = -5

    _response_codes = {
        0: 'OK',
        -1: 'Bad request',
        -2: 'Authentication failed',
        -3: 'Not found',
        -4: 'Method not allowed',
        -5: 'Server error',
    }

    def __init__(self, application, message, *args, **kwargs):
        """A MessageHandler is called at two major points, with regard to the
        eventlet scheduler. __init__ is the first point, which is responsible
        for bootstrapping the state of a single handler.

        __call__ is the second major point.
        """
        self.application = application
        self.message = message
        self._payload = dict()
        self._finished = False
        self.set_status(self._DEFAULT_STATUS)
        self.set_timestamp(int(time.time() * 1000))
        self.initialize()

    def initialize(self):
        """Hook for subclass. Implementers should be aware that this class's
        __init__ calls initialize.
        """
        pass

    def prepare(self):
        """Called before the message handling method. Code here runs prior to
        decorators, so any setup required for decorators to work should happen
        here.
        """
        pass

    @property
    def db_conn(self):
        """Short hand to put database connection in easy reach of handlers
        """
        return self.application.db_conn

    def unsupported(self):
        """Called anytime an unsupported request is made.
        """
        return self.render_error(-1)

    def error(self, err):
        return self.unsupported()

    def add_to_payload(self, key, value):
        """Upserts key-value pair into payload.
        """
        self._payload[key] = value

    def clear_payload(self):
        """Resets the payload but preserves the current status_code.
        """
        status_code = self.status_code
        self._payload = dict() 
        self.set_status(status_code)
        self.initialize()

    def set_status(self, status_code, status_msg=None, extra_txt=None):
        """Sets the status code of the payload to <status_code> and sets
        status msg to the the relevant msg as defined in _response_codes.
        """
        if status_msg is None:
            status_msg = self._response_codes.get(status_code, str(status_code))
        if extra_txt:
            status_msg = '%s - %s' % (status_msg, extra_txt)
        self.add_to_payload(self._STATUS_CODE, status_code)
        self.add_to_payload(self._STATUS_MSG, status_msg)

    @property
    def status_code(self):
        return self._payload[self._STATUS_CODE]
    
    @property
    def status_msg(self):
        return self._payload[self._STATUS_MSG]

    @property
    def current_time(self):
        return self._payload[self._TIMESTAMP]

    def set_timestamp(self, timestamp):
        """Sets the timestamp to given timestamp.
        """
        self.add_to_payload(self._TIMESTAMP, timestamp)
        self.timestamp = timestamp

    def render(self, status_code=None, **kwargs):
        """Renders entire payload as json dump. Subclass and overwrite this
        function if a different output format is needed. See WebMessageHandler
        as an example.
        """
        if not status_code:
            status_code = self.status_code
        self.set_status(status_code)
        rendered = json.dumps(self._payload)
        return rendered

    def render_error(self, status_code, **kwargs):
        """Clears the payload before rendering the error status
        """
        self.clear_payload()
        self._finished = True
        return self.render(status_code=status_code)

    def __call__(self):
        """This function handles mapping the request type to a function on
        the request handler.

        It requires a method attribute to indicate which function on the handler
        should be called. If that function is not supported, call the handlers
        unsupported function.

        In the event that an error has already occurred, _finished will be
        set to true before this function call indicating we should render
        the handler and nothing else.

        In all cases, generating a response for mongrel2 is attempted.
        """
        self.prepare()
        if not self._finished:
            mef = self.message.method.lower() # M-E-T-H-O-D man!

            # Find function mapped to method on self
            if mef in HTTP_METHODS:
                fun = getattr(self, mef, self.unsupported)
            else:
                fun = self.unsupported

            # Call the function we settled on
            try:
                if not hasattr(self, '_url_args') or self._url_args is None:
                    self._url_args = []

                if isinstance(self._url_args, dict):
                    #if the value was optional and not included, filter it out so the functions default takes priority
                    rendered = fun(**dict((k, v) for k,v in self._url_args.items() if v)) 
                else:
                    rendered = fun(*self._url_args)
                if rendered is None:
                    logging.debug('Handler had no return value: %s' % fun)
                    return ''
            except Exception, e:
                logging.error(e, exc_info=True)
                rendered = self.error(e)
                
            self._finished = True
            return rendered
        else:
            return self.render()


class WebMessageHandler(MessageHandler):
    """A base class for common functionality in a request handler.

    Tornado's design inspired this design.
    """
    _DEFAULT_STATUS = 500 # default to server error
    _SUCCESS_CODE = 200
    _AUTH_FAILURE = 401
    _FORBIDDEN = 403
    _NOT_FOUND = 404
    _SERVER_ERROR = 500
    
    _response_codes = {
        200: 'OK',
        400: 'Bad request',
        401: 'Authentication failed',
        403: 'Forbidden',
        404: 'Not found',
        405: 'Method not allowed',
        500: 'Server error',
    }

    ###
    ### Payload extension
    ###
    
    _HEADERS = 'headers'

    def initialize(self):
        """WebMessageHandler extends the payload for body and headers. It
        also provides both fields as properties to mask storage in payload
        """
        self.body = ''
        self.headers = dict()

    def set_body(self, body, headers=None, status_code=_SUCCESS_CODE):
        """
        """
        self.body = body
        self.set_status(status_code)
        if headers is not None:
            self.headers = headers

    ###
    ### Supported HTTP request methods are mapped to these functions
    ###
    def options(self, *args, **kwargs):
        """Default to allowing all of the methods you have defined and public
        """
        supported_methods = []
        for mef in HTTP_METHODS:
            if callable(getattr(self, mef, False)):
                supported_methods.append(mef)
        self.headers["Access-Control-Allow-Methods"] = ", ".join(mef.upper() for mef in supported_methods)
        return self.render()

    def unsupported(self, *args, **kwargs):
        return self.render_error(self._NOT_FOUND)

    def redirect(self, url):
        """Clears the payload before rendering the error status
        """
        logging.debug('Redirecting to url: %s' % url)
        self.clear_payload()
        self._finished = True
        msg = 'Page has moved to %s' % url
        self.set_status(302, status_msg=msg)
        self.headers['Location'] = '%s' % url
        return self.render()

    ###
    ### Helpers for accessing request variables
    ###
    
    def get_argument(self, name, default=None, strip=True):
        """Returns the value of the argument with the given name.

        If the argument appears in the url more than once, we return the
        last value.
        """
        return self.message.get_argument(name, default=default, strip=strip)

    def get_arguments(self, name, strip=True):
        """Returns a list of the arguments with the given name.
        """
        return self.message.get_arguments(name, strip=strip)

    ###
    ### Cookies
    ###

    ### Incoming cookie functions
            
    def get_cookie(self, key, default=None, secret=None):
        """Retrieve a cookie from message, if present, else fallback to
        `default` keyword. Accepts a secret key to validate signed cookies.
        """
        value = default
        if key in self.message.cookies:
            value = self.message.cookies[key].value
        if secret and value:
            dec = cookie_decode(value, secret) 
            return dec[1] if dec and dec[0] == key else None        
        return value

    ### Outgoing cookie functions

    @property
    def cookies(self):
        """Lazy creation of response cookies."""
        if not hasattr(self, "_cookies"):
            self._cookies = Cookie.SimpleCookie()
        return self._cookies

    def set_cookie(self, key, value, secret=None, **kwargs):
        """Add a cookie or overwrite an old one. If the `secret` parameter is
        set, create a `Signed Cookie` (described below).

        `key`: the name of the cookie.
        `value`: the value of the cookie.
        `secret`: required for signed cookies.

        params passed to as keywords:
          `max_age`: maximum age in seconds.
          `expires`: a datetime object or UNIX timestamp.
          `domain`: the domain that is allowed to read the cookie.
          `path`: limits the cookie to a given path

        If neither `expires` nor `max_age` are set (default), the cookie
        lasts only as long as the browser is not closed.
        """
        if secret:
            value = cookie_encode((key, value), secret)
        elif not isinstance(value, basestring):
            raise TypeError('Secret missing for non-string Cookie.')

        # Set cookie value
        self.cookies[key] = value

        # handle keywords
        for k, v in kwargs.iteritems():
            self.cookies[key][k.replace('_', '-')] = v

    def delete_cookie(self, key, **kwargs):
        """Delete a cookie. Be sure to use the same `domain` and `path`
        parameters as used to create the cookie.
        """
        kwargs['max_age'] = -1
        kwargs['expires'] = 0
        self.set_cookie(key, '', **kwargs)

    def delete_cookies(self):
        """Deletes every cookie received from the user.
        """
        for key in self.message.cookies.iterkeys():
            self.delete_cookie(key)
    
    ###
    ### Output generation
    ###

    def convert_cookies(self):
        """ Resolves cookies into multiline values.
        """
        cookie_vals = [c.OutputString() for c in self.cookies.values()]
        if len(cookie_vals) > 0:
            cookie_str = '\nSet-Cookie: '.join(cookie_vals)
            self.headers['Set-Cookie'] = cookie_str

    def render(self, status_code=None, http_200=False, **kwargs):
        """Renders payload and prepares the payload for a successful HTTP
        response.

        Allows forcing HTTP status to be 200 regardless of request status
        for cases where payload contains status information.
        """
        if status_code: 
            self.set_status(status_code)

        # Some API's send error messages in the payload rather than over
        # HTTP. Not necessarily ideal, but supported.
        status_code = self.status_code
        if http_200:
            status_code = 200

        self.convert_cookies()

        response = http_response(self.body, status_code,
                                 self.status_msg, self.headers)

        logging.info('%s %s %s (%s)' % (status_code, self.message.method,
                                        self.message.path,
                                        self.message.remote_addr))
        return response


class JSONMessageHandler(WebMessageHandler):
    """This class is virtually the same as the WebMessageHandler with a slight
    change to how payloads are handled to make them more appropriate for
    representing JSON transmissions.
    """
    def render(self, status_code=None, **kwargs):
        if status_code:
            self.set_status(status_code)

        self.convert_cookies()
        
        self.headers['Content-Type'] = 'application/json'

        body = json.dumps(self._payload)

        response = http_response(body, self.status_code,
                                 self.status_msg, self.headers)

        logging.info('%s %s %s (%s)' % (self.status_code, self.message.method,
                                        self.message.path,
                                        self.message.remote_addr))
        return response


class JsonSchemaMessageHandler(WebMessageHandler):
    manifest = {}

    @classmethod
    def add_model(self, model):
        self.manifest[model.__name__.lower()]  = model.for_jsonschema()

    def get(self):
        self.set_body(json.dumps(self.manifest.values()))
        return self.render(status_code=200)

    def render(self, status_code=None, **kwargs):
        if status_code:
            self.set_status(status_code)

        self.convert_cookies()
        self.headers['Content-Type'] = "application/schema+json"


        response = http_response(self.body, status_code,
                                 self.status_msg, self.headers)
        
        return response

MULTIPLE_ITEM_SEP = ','

class AutoAPIBase(JSONMessageHandler):
    model = None
    queries = None 

    ###
    ### configuring input and output formats
    ###

    def _get_shields_from_postbody(self):
        """ Describes how our incoming data looks
        """
        items = json.loads(str(self.get_argument('data'))) #ujson doesn't take unicode
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





###
### Application logic
###

class Brubeck(object):

    def __init__(self, mongrel2_pair=None, handler_tuples=None, pool=None,
                 no_handler=None, base_handler=None, template_loader=None,
                 log_level=logging.INFO, login_url=None, db_conn=None,
                 cookie_secret=None,
                 *args, **kwargs):
        """Brubeck is a class for managing connections to Mongrel2 servers
        while providing an asynchronous system for managing message handling.

        mongrel2_pair should be a 2-tuple consisting of the pull socket address
        and the pub socket address for communicating with Mongrel2. Brubeck
        creates and manages a Mongrel2Connection instance from there.

        handler_tuples is a list of two-tuples. The first item is a regex
        for matching the URL requested. The second is the class instantiated
        to handle the message.
        """
        # All output is sent via logging
        # (while i figure out how to do a good abstraction via zmq)
        logging.basicConfig(level=log_level)

        # Log whether we're using eventlet or gevent.
        logging.info('Using coroutine library: %s' % CORO_LIBRARY)

        # A Mongrel2Connection is currently just a way to manage
        # the sockets we need to open with a Mongrel2 instance and
        # identify this particular Brubeck instance as the sender
        if mongrel2_pair is not None:
            (pull_addr, pub_addr) = mongrel2_pair
            self.m2conn = Mongrel2Connection(pull_addr, pub_addr)
        else:
            raise ValueError('No mongrel2 connection possible.')

        # Class based route lists should be handled this way.
        # It is also possible to use `add_route`, a decorator provided by a
        # brubeck instance, that can extend routing tables.
        self.handler_tuples = handler_tuples
        if self.handler_tuples is not None:
            self.init_routes(handler_tuples)

        # We can accept an existing pool or initialize a new pool
        if pool is None:
            self.pool = coro_pool()
        elif callable(pool):
            self.pool = pool()
        else:
            raise ValueError('Unable to initialize coroutine pool')

        # Set a base_handler for handling errors (eg. 404 handler)
        self.base_handler = base_handler
        if self.base_handler is None:
            self.base_handler = WebMessageHandler

        # A database connection is optional. The var name is now in place
        self.db_conn = db_conn

        # Login url is optional
        self.login_url = login_url
            
        # This must be set to use secure cookies
        self.cookie_secret = cookie_secret

        # Any template engine can be used. Brubeck just needs a function that
        # loads the environment without arguments. 
        if callable(template_loader):
            loaded_env = template_loader()
            if loaded_env:
                self.template_env = loaded_env
            else:
                raise ValueError('template_env failed to load.')

    ###
    ### Message routing functions
    ###
    
    def init_routes(self, handler_tuples):
        """Loops over a list of (pattern, handler) tuples and adds them
        to the routing table.
        """
        for ht in handler_tuples:
            (pattern, kallable) = ht
            self.add_route_rule(pattern, kallable)

    def add_route_rule(self, pattern, kallable):
        """Takes a string pattern and callable and adds them to URL routing.
        The pattern should be compilable as a regular expression with `re`.
        The kallable argument should be a handler.
        """
        if not hasattr(self, '_routes'):
            self._routes = list()
        regex = re.compile(pattern, re.UNICODE)
        self._routes.append((regex, kallable))

    def add_route(self, url_pattern, method=None):
        """A decorator to facilitate building routes wth callables. Can be
        used as alternative method for constructing routing tables.
        """
        if method is None:
            method = list()
        elif not hasattr(method, '__iter__'):
            method = [method]
            
        def decorator(kallable):
            """Decorates a function by adding it to the routing table and adding
            code to check the HTTP Method used.
            """
            def check_method(app, msg, *args):
                """Create new method which checks the HTTP request type.
                If URL matches, but unsupported request type is used an
                unsupported error is thrown.

                def one_more_layer():
                    INCEPTION
                """
                if msg.method not in method:
                    return self.base_handler(app, msg).unsupported()
                else:
                    return kallable(app, msg, *args)
                
            self.add_route_rule(url_pattern, check_method)
            return check_method
        return decorator

    def route_message(self, message):
        """Factory function that instantiates a request handler based on
        path requested.

        If a class that implements `__call__` is used, the class should
        implement an `__init__` that receives two arguments: a brubeck instance
        and the message to be handled. The return value of this call is a
        callable class that is ready to be executed in a follow up coroutine.

        If a function is used (eg with the decorating routing pattern) a
        closure is created around the two arguments. The return value of this
        call is a function ready to be executed in a follow up coroutine.
        """
        handler = None
        for (regex, kallable) in self._routes:
            url_check = regex.match(message.path)

            if url_check:
                # `None` will fail, so we have to use at least an empty list
                # We should try to use named arguments first, and if they're not present
                # fall back to positional arguments
                url_args = url_check.groupdict() or url_check.groups() or []

                if inspect.isclass(kallable):
                    # Handler classes must be instantiated
                    handler = kallable(self, message)
                    # Attach url args to handler
                    handler._url_args = url_args
                    return handler
                else:
                    # Can't instantiate a function
                    if isinstance(url_args, dict):
                        #if the value was optional and not included, filter it out so the functions default takes priority
                        handler = lambda: kallable(self, message, **dict((k, v) for k,v in url_args.items() if v))
                    else:
                        handler = lambda: kallable(self, message, *url_args)
                    return handler
            
        if handler is None:
            handler = self.base_handler(self, message)

        return handler

    def register_api(self, APIClass):
        model, model_name = APIClass.model, APIClass.model.__name__.lower()

        if not JsonSchemaMessageHandler.manifest:
            manifest_pattern = "/manifest.json"
            self.add_route_rule(manifest_pattern, JsonSchemaMessageHandler)
        
        pattern = "/" + model_name  + "/((?P<item_ids>[-\w\d%s]+)/|$)" % MULTIPLE_ITEM_SEP
        self.add_route_rule(pattern, APIClass)
        JsonSchemaMessageHandler.add_model(model)

        

    ###
    ### Application running functions
    ###

    def run(self):
        """This method turns on the message handling system and puts Brubeck
        in a never ending loop waiting for messages.

        The loop is actually the eventlet scheduler. A goal of Brubeck is to
        help users avoid thinking about complex things like an event loop while
        still getting the goodness of asynchronous and nonblocking I/O.
        """
        greeting = 'Brubeck v%s online ]-----------------------------------'
        print greeting % version
        
        try:
            while True:
                request = self.m2conn.recv()
                if request.is_disconnect():
                    continue
                else:
                    coro_spawn(route_message, self, request)
        except KeyboardInterrupt, ki:
            # Put a newline after ^C
            print '\nBrubeck going down...'
