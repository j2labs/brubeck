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
    handler.message = message
    handler.application = application
    spawn_n(request_handler, handler)

    
def request_handler(handler):
    """Coroutine for handling the request itself. It simply returns the request
    path in reverse for now.
    """
    if callable(handler):
        response = handler()
        spawn_n(result_handler, handler, response)
    
def result_handler(handler, response):
    """The request has been processed and this is called to do any post
    processing and then send the data back to mongrel2.
    """
    handler.application.m2conn.reply(handler.message, response)


###
### Message handling
###

class MessageHandler(object):
    """A base class for request handling

    Contains the general payload mechanism used for storing key-value pairs
    to answer requests.

    No render function is defined here so this class should not actually be
    used. 
    """
    SUPPORTED_METHODS = ()
    _STATUS_CODE = 'status_code'
    _STATUS_MSG = 'status_msg'
    _TIMESTAMP = 'timestamp'
    _DEFAULT_STATUS = -1 # default to error, earn success

    _response_codes = {
        0: 'OK',
        -1: 'Bad request',
        -2: 'Authentication failed',
        -3: 'Not found',
        -4: 'Method not allowed',
        -5: 'Server error',
    }

    def __init__(self, *args, **kwargs):
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
        """Called anytime an unsupported request is made
        """
        return self.render_error(-1)

    def add_to_payload(self, key, value):
        """Upserts key-value pair into payload.
        """
        self._payload[key] = value

    def clear_payload(self):
        """Resets the payload.
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
        """Sets the timestamp to given timestamp
        """
        self.add_to_payload(self._TIMESTAMP, timestamp)
        self.timestamp = timestamp

    def render(self, *kwargs):
        """Don't actually use this class. Subclass it so render can handle
        templates or making json or whatevz you got in mind.
        """
        raise NotImplementedError('Someone code me! PLEASE!')

    def render_error(self, status_code, **kwargs):
        """Clears the payload before rendering the error status
        """
        self.clear_payload()
        self.set_status(status_code, **kwargs)
        return self.render()

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
            # M-E-T-H-O-D MAN!
            mef = self.message.method
            if mef in self.SUPPORTED_METHODS:
                mef = mef.lower()
                fun = getattr(self, mef)
            else:
                fun = self.unsupported

            try:
                response = fun(*args, **kwargs)
            except Exception, e:
                logging.error(e)
                response = self.unsupported()
                
            self._finished = True
            return response
        else:
            return self.render()


class WebMessageHandler(MessageHandler):
    """A base class for common functionality in a request handler.

    Tornado's design inspired this design.
    """
    SUPPORTED_METHODS = ("GET", "HEAD", "POST", "DELETE", "PUT", "OPTIONS")
    _DEFAULT_STATUS = 500 # default to server error

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
    def body(self):
        return self._payload[self._BODY]

    @property
    def headers(self):
        return self._payload[self._HEADERS]

    def set_body(self, body, headers=None):
        self._payload[self._BODY] = body
        if headers is not None:
            self._payload[self._HEADERS] = headers
        
    ###
    ### Request types supported are mapped to HTTP request methods
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

        If default is not provided, the argument is considered to be
        required, and we throw an HTTP 404 exception if it is missing.

        If the argument appears in the url more than once, we return the
        last value.

        The returned value is always unicode.
        """
        args = self.get_arguments(name, strip=strip)
        if not args:
            if default is None:
                return self.render_error(404, extra_txt=name)
            return default
        return args[-1]

    def get_arguments(self, name, strip=True):
        """Returns a list of the arguments with the given name.

        If the argument is not present, returns an empty list.

        The returned values are always unicode.
        """
        values = self.message.arguments.get(name, [])
        # Get rid of any weird control chars
        values = [re.sub(r"[\x00-\x08\x0e-\x1f]", " ", x) for x in values]
        values = [unicode(x) for x in values]
        if strip:
            values = [x.strip() for x in values]
        return values


    http_format = "HTTP/1.1 %(code)s %(status)s\r\n%(headers)s\r\n\r\n%(body)s"
    def render(self, http_200=False, **kwargs):
        """Renders payload and prepares HTTP response.

        Allows forcing HTTP status to be 200 regardless of request status.
        """
        payload = dict(code=self.status_code,
                       status=self.status_msg,
                       body=self.body)

        # Some API's send error messages in the payload rather than over
        # HTTP. Not by ideal, but supported.
        if http_200:
            payload['code'] = 200

        content_length = 0
        if self.body is not None:
            content_length = len(self.body)
        self.headers['Content-Length'] = content_length
        
        payload['headers'] = "\r\n".join('%s: %s' % (k,v)
                                         for k,v in self.headers.items())

        return self.http_format % payload


###
### Subclasses for different message rendering.
###

class JSONMessageHandler(WebMessageHandler):
    """JSONRequestHandler is a system for maintaining a payload until the
    request is handled to completion. It offers rendering functions for
    printing the payload into JSON format.
    """
    def render(self, **kwargs):
        """Renders payload as json
        """
        self.body = json.dumps(self._payload)
        rendered = super(self, JSONRequestHandler).render(**kwargs)
        return rendered


###
### Application logic
###

class Brubeck(object):
    def __init__(self, m2_sockets, handler_tuples=None, pool=None,
                 no_handler=None, base_handler=None, template_loader=None,
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

        # A Mongrel2Connection is currently just a way to manage
        # the sockets we need to open with a Mongrel2 instance and
        # identify this particular Brubeck instance as the sender
        (pull_addr, pub_addr) = m2_sockets
        self.m2conn = Mongrel2Connection(pull_addr, pub_addr)

        # The details of the routing aren't exposed
        self.init_routes(handler_tuples)

        # I am interested in making the app compatible with existing eventlet
        # apps already running with a scheduler. I am not sure if this is the
        # right way...
        self.pool = pool
        if self.pool is None:
            self.pool = eventlet.GreenPool()

        # Set a base_handler for handling errors (eg. missing handler)
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
                raise ValueException('template_env failed to load')

    ###
    ### Message routing funcitons
    ###
    
    def init_routes(self, handler_tuples):
        """Creates the _routes variable and compile route patterns
        """
        self._routes = list()
        for ht in handler_tuples:
            (pattern, cls) = ht
            regex = re.compile(pattern)
            self._routes.append((regex, cls))

    def route_message(self, message):
        """Factory funciton that instantiates a request handler based on
        path requested.
        """
        handler = None
        for (regex, handler_cls) in self._routes:
            if regex.search(message.path):
                handler = handler_cls(self, message)

        if handler is None:
            handler = self.base_handler()

        return handler

    ###
    ### Application running functions
    ###

    def run(self):
        """This method turns on the message handling system and puts Brubeck
        in a never ending loop waiting for messages.
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

