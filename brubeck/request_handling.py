#!/usr/bin/env python


"""Brubeck is a coroutine oriented zmq message handling framework. I learn by
doing and this code base represents where my mind has wandered with regard to
concurrency.

If you are building a message handling system you should import this class
before anything else to guarantee the eventlet code is run first.

See github.com/j2labs/brubeck for more information.
"""

import eventlet
from eventlet import spawn, spawn_n, serve
from eventlet.green import zmq
from eventlet.hubs import get_hub, use_hub
use_hub('zeromq')

from . import version

from uuid import uuid4
import os
import sys
import re
import time
import logging
import inspect

from mongrel2 import Mongrel2Connection
from functools import partial


###
### Common helpers
###

def curtime():
    """This funciton is the central method for getting the current time. It
    represents the time in milliseconds and the timezone is UTC.
    """
    return long(time.time() * 1000)

HTTP_FORMAT = "HTTP/1.1 %(code)s %(status)s\r\n%(headers)s\r\n\r\n%(body)s"
def http_response(body, code, status, headers):
    """Renders payload and prepares HTTP response.
    """
    payload = {'code': code, 'status': status, 'body': body}
    content_length = 0
    if body is not None:
        content_length = len(body)
    headers['Content-Length'] = content_length
    payload['headers'] = "\r\n".join('%s: %s' % (k,v) for k,v in
                                     headers.items())
    return HTTP_FORMAT % payload


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
    spawn_n(request_handler, application, message, handler)

def request_handler(application, message, handler):
    """Coroutine for handling the request itself. It simply returns the request
    path in reverse for now.
    """
    if callable(handler):
        response = handler()
        spawn_n(result_handler, application, message, response)
    
def result_handler(application, message, response):
    """The request has been processed and this is called to do any post
    processing and then send the data back to mongrel2.
    """
    application.m2conn.reply(message, response)


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

    Two callbacks are offered for state preperation.

    The `initialize` function allows users to add steps to object
    initialization. A mixin, however, should never use this. You could hook
    the request handler up to a database connection pool, for example.

    The `prepare` function is called just before any decorators are called.
    The idea here is to give Mixin creators a chance to build decorators that
    depend on post-initialization processing to have taken place. You could use
    that database connection we created in `initialize` to check the username
    and password from a user.
    """
    SUPPORTED_METHODS = ()
    _STATUS_CODE = 'status_code'
    _STATUS_MSG = 'status_msg'
    _TIMESTAMP = 'timestamp'
    _DEFAULT_STATUS = -1 # default to error, earn success
    _SUCCESS_CODE = 0

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

    def unsupported(self):
        """Called anytime an unsupported request is made.
        """
        return self.render_error(-1)

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

    def set_status(self, status_code, extra_txt=None):
        """Sets the status code of the payload to <status_code> and sets
        status msg to the the relevant msg as defined in _response_codes.
        """
        status_msg = self._response_codes[status_code]
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

    def __call__(self, *args, **kwargs):
        """This function handles mapping the request type to a function on
        the request handler.

        It requires a method attribute to indicate which function on the handler
        should be called. If that function is not supported, call the handlers
        unsupported function.

        In the event that an error has already occurred, _finished will be
        set to true before this funciton call indicating we should render
        the handler and nothing else.

        In all cases, generating a response for mongrel2 is attempted.
        """
        self.prepare()
        if not self._finished:
            mef = self.message.method # M-E-T-H-O-D man!

            # Find function mapped to method on self
            if mef in self.SUPPORTED_METHODS:
                mef = mef.lower()
                fun = getattr(self, mef)
            else:
                fun = self.unsupported

            # Call the function we settled on
            try:
                rendered = fun(*args, **kwargs)
            except Exception, e:
                logging.error(e)
                rendered = self.unsupported()
                
            self._finished = True
            return rendered
        else:
            return self.render()


class WebMessageHandler(MessageHandler):
    """A base class for common functionality in a request handler.

    Tornado's design inspired this design.
    """
    SUPPORTED_METHODS = ("GET", "HEAD", "POST", "DELETE", "PUT", "OPTIONS")
    _DEFAULT_STATUS = 500 # default to server error
    _SUCCESS_CODE = 200

    _response_codes = {
        200: 'OK',
        400: 'Bad request',
        401: 'Authentication failed',
        404: 'Not found',
        405: 'Method not allowed',
        500: 'Server error',
    }

    ###
    ### Payload extension
    ###
    
    _BODY = '_body'
    _HEADERS = '_headers'

    def initialize(self):
        """WebMessageHandler extends the payload for body and headers. It
        also provides both fields as properties to mask storage in payload
        """
        self._payload[self._BODY] = ''
        self._payload[self._HEADERS] = dict()

    @property
    def headers(self):
        return self._payload[self._HEADERS]

    @property
    def body(self):
        return self._payload[self._BODY]

    def set_body(self, body, headers=None):
        self._payload[self._BODY] = body
        if headers is not None:
            self._payload[self._HEADERS] = headers
        
    ###
    ### Supported HTTP request methods are mapped to these functions
    ###

    def head(self, *args, **kwargs):
        return self.unsupported()

    def get(self, *args, **kwargs):
        return self.unsupported()

    def post(self, *args, **kwargs):
        return self.unsupported()

    def delete(self, *args, **kwargs):
        return self.unsupported()

    def put(self, *args, **kwargs):
        return self.unsupported()

    def options(self, *args, **kwargs):
        """Should probably implement this in this class. Got any ideas?
        """
        return self.unsupported()

    def unsupported(self, *args, **kwargs):
        return self.render_error(404)

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

    def render(self, status_code=None, http_200=False, **kwargs):
        """Renders payload and prepares the payload for a successful HTTP
        response.

        Allows forcing HTTP status to be 200 regardless of request status
        for cases where payload contains status information.
        """
        if not status_code:
            status_code = self._SUCCESS_CODE
        self.set_status(status_code)

        # Some API's send error messages in the payload rather than over
        # HTTP. Not necessarily ideal, but supported.
        if http_200:
            status_code = 200

        # TODO fill in REMOTE_ADDR 
        logging.info('%s %s %s (%s)' % (status_code,
                                        self.message.method,
                                        self.message.path,
                                        'REMOTE_ADDR'))

        return http_response(self.body, status_code, self.status_msg, self.headers)


###
### Application logic
###

class Brubeck(object):
    def __init__(self, mongrel2_pair=None, handler_tuples=None, pool=None,
                 no_handler=None, base_handler=None, template_loader=None,
                 log_level=logging.INFO,
                 *args, **kwargs):
        """Brubeck is a class for managing connections to Mongrel2 servers
        while providing an asynchronous system for managing message handling.

        m2_sockets should be a 2-tuple consisting of the pull socket address
        and the pub socket address for communicating with Mongrel2. Brubeck
        creates and manages a Mongrel2Connection instance from there.

        request_handlers is a list of two-tuples. The first item is a regex
        for matching the URL requested. The second is the class instantiated
        to handle the message.
        """
        # All output is sent via logging
        # (while i figure out how to do a good abstraction via zmq)
        logging.basicConfig(level=log_level)

        # A Mongrel2Connection is currently just a way to manage
        # the sockets we need to open with a Mongrel2 instance and
        # identify this particular Brubeck instance as the sender
        if mongrel2_pair is not None:
            (pull_addr, pub_addr) = mongrel2_pair
            self.m2conn = Mongrel2Connection(pull_addr, pub_addr)
        else:
            raise ValueException('No mongrel2 connection possible.')

        # Class based route lists should be handled this way.
        # It is also possible to use `add_route`, a decorator provided by a
        # brubeck instance, that can extend routing tables.
        self.handler_tuples = handler_tuples
        if self.handler_tuples is not None:
            self.init_routes(handler_tuples)

        # I am interested in making the app compatible with existing eventlet
        # apps already running with a scheduler. I am not sure if this is the
        # right way...
        self.pool = pool
        if self.pool is None:
            self.pool = eventlet.GreenPool()

        # Set a base_handler for handling errors (eg. 404 handler)
        self.base_handler = base_handler
        if self.base_handler is None:
            self.base_handler = WebMessageHandler

        # Any template engine can be used. Brubeck just needs a function that
        # loads the environment without arguments. 
        if callable(template_loader):
            loaded_env = template_loader()
            if loaded_env:
                self.template_env = loaded_env
            else:
                raise ValueException('template_env failed to load.')

    ###
    ### Message routing funcitons
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
        regex = re.compile(pattern)
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
            def check_method(app, msg):
                """Create new method which checks the HTTP request type.
                If URL matches, but unsupported request type is used an
                unsupported error is thrown.

                def one_more_layer():
                    print 'INCEPTION'
                """
                if msg.method not in method:
                    return self.base_handler(app, msg).unsupported()
                else:
                    return kallable(app, msg)
                
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
            if regex.search(message.path):
                if inspect.isclass(kallable):
                     # Handler classes must be instantiated
                    handler = kallable(self, message)
                else:
                    # Can't instantiate a function
                    handler = lambda: kallable(self, message)
            else:
                logging.debug('Msg path not found: %s' % (message.path))

        if handler is None:
            handler = self.base_handler(self, message)

        return handler

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
                self.pool.spawn_n(route_message, self, request)
        except KeyboardInterrupt, ki:
            # Put a newline after ^C
            print '\nBrubeck going down...'
