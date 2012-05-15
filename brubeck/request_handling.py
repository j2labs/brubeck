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

    coro_pool = pool.Pool

    def coro_spawn(function, app, message, *a, **kw):
        app.pool.spawn(function, app, message, *a, **kw)

    CORO_LIBRARY = 'gevent'

### Fallback to eventlet
except ImportError:
    try:
        import eventlet
        eventlet.patcher.monkey_patch(all=True)

        coro_pool = eventlet.GreenPool

        def coro_spawn(function, app, message, *a, **kw):
            app.pool.spawn_n(function, app, message, *a, **kw)

        CORO_LIBRARY = 'eventlet'

    except ImportError:  # eventlet or gevent is required.
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
import os, sys
from dictshield.base import ShieldException
from request import Request, to_bytes, to_unicode

import ujson as json

###
### Common helpers
###

HTTP_METHODS = ['get', 'post', 'put', 'delete',
                'head', 'options', 'trace', 'connect']

HTTP_FORMAT = "HTTP/1.1 %(code)s %(status)s\r\n%(headers)s\r\n\r\n%(body)s"


class FourOhFourException(Exception):
    pass


def http_response(body, code, status, headers):
    """Renders arguments into an HTTP response.
    """
    payload = {'code': code, 'status': status, 'body': body}
    content_length = 0
    if body is not None:
        content_length = len(to_bytes(body))
    headers['Content-Length'] = content_length
    payload['headers'] = "\r\n".join('%s: %s' % (k, v)
                                     for k, v in headers.items())

    return HTTP_FORMAT % payload

def _lscmp(a, b):
    """Compares two strings in a cryptographically safe way
    """
    return not sum(0 if x == y else 1
                   for x, y in zip(a, b)) and len(a) == len(b)


###
### Message handling coroutines
###

### WSGI

def receive_wsgi_message(application, environ, callback):
    request = Request.parse_wsgi_request(environ)
    handler = application.route_message(request)
    response = handler()
    x = callback(response['status'], response['headers'])
    return [str(response['body'])]

### Mongrel2

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
    _DEFAULT_STATUS = -1  # default to error, earn success
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

    def on_finish(self):
        """Called after the message handling method. Counterpart to prepare
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
            status_msg = self._response_codes.get(status_code,
                                                  str(status_code))
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

    def render(self, status_code=None, hide_status=False, **kwargs):
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

        It requires a method attribute to indicate which function on the
        handler should be called. If that function is not supported, call the
        handlers unsupported function.

        In the event that an error has already occurred, _finished will be
        set to true before this function call indicating we should render
        the handler and nothing else.

        In all cases, generating a response for mongrel2 is attempted.
        """
        try:
            self.prepare()
            if not self._finished:
                mef = self.message.method.lower()  # M-E-T-H-O-D man!

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
                        ### if the value was optional and not included, filter it
                        ### out so the functions default takes priority
                        kwargs = dict((k, v)
                                      for k, v in self._url_args.items() if v)
                        rendered = fun(**kwargs)
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
        finally:
            self.on_finish()


class WebMessageHandler(MessageHandler):
    """A base class for common functionality in a request handler.

    Tornado's design inspired this design.
    """
    _DEFAULT_STATUS = 500  # default to server error
    _SUCCESS_CODE = 200
    _UPDATED_CODE = 200
    _CREATED_CODE = 201
    _MULTI_CODE = 207
    _FAILED_CODE = 400
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
        allowed_methods = ", ".join(mef.upper() for mef in supported_methods)
        self.headers["Access-Control-Allow-Methods"] = allowed_methods
        self.set_status(200)
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

        if self.message.is_wsgi:
            response  = {
                'body' : self.body,
                'status' : str(status_code) + ' ' + self.status_msg,
                'headers' : [(k, v) for k,v in self.headers.items()]
                }
        
        else:
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

    The `hide_status` flag is used to reduce the payload down to just the data.
    """
    def render(self, status_code=None, hide_status=False, **kwargs):
        if status_code:
            self.set_status(status_code)

        self.convert_cookies()

        self.headers['Content-Type'] = 'application/json'

        if hide_status and 'data' in self._payload:
            body = json.dumps(self._payload['data'])
        else:
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
        self.manifest[model.__name__.lower()] = model.for_jsonschema()

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

###
### Application logic
###

class Brubeck(object):

    MULTIPLE_ITEM_SEP = ','

    def __init__(self, msg_conn=None, handler_tuples=None, pool=None,
                 no_handler=None, base_handler=None, template_loader=None,
                 log_level=logging.INFO, login_url=None, db_conn=None,
                 cookie_secret=None, api_base_url=None,
                 *args, **kwargs):
        """Brubeck is a class for managing connections to webservers. It
        supports Mongrel2 and WSGI while providing an asynchronous system for
        managing message handling.

        `msg_conn` should be a `connections.Connection` instance.

        `handler_tuples` is a list of two-tuples. The first item is a regex
        for matching the URL requested. The second is the class instantiated
        to handle the message.

        `pool` can be an existing coroutine pool, but one will be generated if
        one isn't provided.

        `base_handler` is a class that Brubeck can rely on for implementing
        error handling functions.

        `template_loader` is a function that builds the template loading
        environment.

        `log_level` is a log level mapping to Python's `logging` module's
        levels.

        `login_url` is the default URL for a login screen.

        `db_conn` is a database connection to be shared in this process

        `cookie_secret` is a string to use for signing secure cookies.
        """
        # All output is sent via logging
        # (while i figure out how to do a good abstraction via zmq)
        logging.basicConfig(level=log_level)

        # Log whether we're using eventlet or gevent.
        logging.info('Using coroutine library: %s' % CORO_LIBRARY)

        # Attach the web server connection
        if msg_conn is not None:
            self.msg_conn = msg_conn
        else:
            raise ValueError('No web server connection provided.')

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

        # API base url is optional
        if api_base_url is None:
            self.api_base_url = '/'
        else:
            self.api_base_url = api_base_url

        # This must be set to use secure cookies
        self.cookie_secret = cookie_secret

        # Any template engine can be used. Brubeck just needs a function that
        # loads the environment without arguments.
        #
        # It then creates a function that renders templates with the given
        # environment and attaches it to self.
        if callable(template_loader):
            loaded_env = template_loader()
            if loaded_env:
                self.template_env = loaded_env

                # Create template rendering function
                def render_template(template_file, **context):
                    """Renders template using provided template environment.
                    """
                    if hasattr(self, 'template_env'):
                        t_env = self.template_env
                        template = t_env.get_template(template_file)
                        body = template.render(**context or {})
                    return body

                # Attach it to brubeck app (self)
                setattr(self, 'render_template', render_template)
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
            """Decorates a function by adding it to the routing table and
            adding code to check the HTTP Method used.
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
                ### `None` will fail, so we have to use at least an empty list
                ### We should try to use named arguments first, and if they're
                ### not present fall back to positional arguments
                url_args = url_check.groupdict() or url_check.groups() or []

                if inspect.isclass(kallable):
                    ### Handler classes must be instantiated
                    handler = kallable(self, message)
                    ### Attach url args to handler
                    handler._url_args = url_args
                    return handler
                else:
                    ### Can't instantiate a function
                    if isinstance(url_args, dict):
                        ### if the value was optional and not included, filter
                        ### it out so the functions default takes priority
                        kwargs = dict((k, v) for k, v in url_args.items() if v)

                        handler = lambda: kallable(self, message, **kwargs)
                    else:
                        handler = lambda: kallable(self, message, *url_args)
                    return handler

        if handler is None:
            handler = self.base_handler(self, message)

        return handler

    def register_api(self, APIClass, prefix=None):
        model, model_name = APIClass.model, APIClass.model.__name__.lower()

        if not JsonSchemaMessageHandler.manifest:
            manifest_pattern = "/manifest.json"
            self.add_route_rule(manifest_pattern, JsonSchemaMessageHandler)

        if prefix is None:
            url_prefix = self.api_base_url + model_name
        else:
            url_prefix = prefix

        # TODO inspect url pattern for holes
        pattern = "/((?P<ids>[-\w\d%s]+)(/)*|$)" % self.MULTIPLE_ITEM_SEP
        api_url = ''.join([url_prefix, pattern])

        self.add_route_rule(api_url, APIClass)
        JsonSchemaMessageHandler.add_model(model)


    ###
    ### Application running functions
    ###

    def recv_forever_ever(self):
        """Helper function for starting the link between Brubeck and the
        message processing provided by `msg_conn`.
        """
        mc = self.msg_conn
        mc.recv_forever_ever(self)

    def run(self):
        """This method turns on the message handling system and puts Brubeck
        in a never ending loop waiting for messages.

        The loop is actually the eventlet scheduler. A goal of Brubeck is to
        help users avoid thinking about complex things like an event loop while
        still getting the goodness of asynchronous and nonblocking I/O.
        """
        greeting = 'Brubeck v%s online ]-----------------------------------'
        print greeting % version

        self.recv_forever_ever()
