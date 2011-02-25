#!/usr/bin/env python


"""Brubeck is a coroutine oriented zmq message handling framework. I learn by
doing and this code base represents where my mind has wandered with regard to
concurrency.

See github.com/j2labs/brubeck for more information.
"""

import eventlet
from eventlet import spawn, spawn_n, serve
from eventlet.green import zmq
from eventlet.hubs import get_hub, use_hub
use_hub('zeromq')

from uuid import uuid1
import os
import sys
import re

from mongrel2 import Mongrel2Connection, http_response
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

def route_request(application, request):
    """This is the first of the three coroutines called. It looks at the
    request, determines which handler will be used to execute it, and
    spawns a coroutine to run that handler.
    """
    handler = None
    for h in application.request_handlers:
        (p, rh) = h
        regex = re.compile(p)
        if regex.search(request.path):
            handler = rh(application, request)
            
    if handler is None:
        handler = WebRequestHandler(application, request)

    handler.request = request
    handler.application = application
    spawn_n(request_handler, handler)

    
def request_handler(handler):
    """Coroutine for handling the request itself. It simply returns the request
    path in reverse for now.
    """
    response = handler._execute()
    spawn_n(result_handler, handler, response)

    
def result_handler(handler, response):
    """The request has been processed and this is called to do any post
    processing and then send the data back to mongrel2.
    """
    handler.application.m2conn.reply(handler.request, response)


###
### Request handling
###

class RequestHandler(Exception):
    """A base class for exceptions used by bott^N^N^N^Nbrubeck.

    Contains the general payload mechanism used for storing key-value pairs
    to answer requests.
    """
    STATUS_CODE = 'status_code'
    STATUS_MSG = 'status_msg'
    TIMESTAMP = 'timestamp'
    DEFAULT_STATUS = -1 # default to error, earn success

    _response_codes = {
        0: 'OK',
        -1: 'Server error',
        -2: 'Method unsupported',
        -3: 'Authentication failed',
        -4: 'Missing argument',
    }

    def __init__(self, *args, **kwargs):
        super(RequestHandler, self).__init__(*args, **kwargs)
        self._payload = dict()
        self._finished = False
        self.set_status(self.DEFAULT_STATUS)
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

    def add_to_payload(self, key, value):
        """Upserts key-value pair into payload.
        """
        self._payload[key] = value

    def clear_payload(self):
        """Resets the payload.
        """
        self._payload[key] = dict() # beware of mutable default values

    def set_status(self, status_code, extra_txt=None):
        """Sets the status code of the payload to <status_code> and sets
        status msg to the the relevant msg as defined in _response_codes.
        """
        status_msg = self._response_codes[status_code]
        if extra_txt:
            status_msg = '%s - %s' % (status_msg, extra_txt)
        self.add_to_payload(self.STATUS_CODE, status_code)
        self.add_to_payload(self.STATUS_MSG, status_msg)

    @property
    def status_code(self):
        return self._payload[self.STATUS_CODE]
    
    @property
    def status_msg(self):
        return self._payload[self.STATUS_MSG]

    def set_timestamp(self, timestamp):
        """Sets the timestamp to given timestamp
        """
        self.add_to_payload(self.TIMESTAMP, timestamp)
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
        raise

    def _execute(self, *args, **kwargs):
        """This function handles mapping the request type to a function on
        the request handler.

        If an error occurs, render is called to handle the exception bubbling
        up from anywhere in the stack.
        """
        self.prepare()
        if not self._finished:
            fun = getattr(self, self.request.method.lower())
            # I got this neat technique from defnull's bottle
            try:
                # a function is expected to render itself
                response = fun(*args, **kwargs)
            except RequestHandler, rh:
                # unless it's an error
                response = rh.render()
            except Exception, e:
                raise
            return response


class WebRequestHandler(RequestHandler):
    """A base class for common functionality in a request handler.

    Tornado's design inspired this design.
    """
    SUPPORTED_METHODS = ("GET", "HEAD", "POST", "DELETE", "PUT", "OPTIONS")
    DEFAULT_STATUS = 500 # default to server error

    _response_codes = {
        200: 'OK',
        400: 'Bad request',
        401: 'Authentication failed',
        404: 'Not found',
        405: 'Method not allowed',
        500: 'Server error',
    }

    # override these to implement handling of HTTP method types
    def head(self, *args, **kwargs):
        self.unsupported()

    def get(self, *args, **kwargs):
        self.unsupported()

    def post(self, *args, **kwargs):
        self.unsupported()

    def delete(self, *args, **kwargs):
        self.unsupported()

    def put(self, *args, **kwargs):
        self.unsupported()

    def options(self, *args, **kwargs):
        self.unsupported()

    def unsupported(self):
        self.set_status(405)
        raise self

    _ARG_DEFAULT = list()
    def get_argument(self, name, default=_ARG_DEFAULT, strip=True):
        """Returns the value of the argument with the given name.

        If default is not provided, the argument is considered to be
        required, and we throw an HTTP 404 exception if it is missing.

        If the argument appears in the url more than once, we return the
        last value.

        The returned value is always unicode.
        """
        args = self.get_arguments(name, strip=strip)
        if not args:
            if default is self._ARG_DEFAULT:
                self.set_status(-4, extra_txt=name)
                raise 
            return default
        return args[-1]

    def get_arguments(self, name, strip=True):
        """Returns a list of the arguments with the given name.

        If the argument is not present, returns an empty list.

        The returned values are always unicode.
        """
        values = self.request.data.get(name, [])
        # Get rid of any weird control chars
        values = [re.sub(r"[\x00-\x08\x0e-\x1f]", " ", x) for x in values]
        values = [_unicode(x) for x in values]
        if strip:
            values = [x.strip() for x in values]
        return values    

    @property
    def current_user(self):
        """The authenticated user for this request.

        Determined by either get_current_user, which you can override to
        set the user based on, e.g., a cookie. If that method is not
        overridden, this method always returns None.

        We lazy-load the current user the first time this method is called
        and cache the result after that.
        """
        if not hasattr(self, "_current_user"):
            self._current_user = self.get_current_user()
        return self._current_user        

    def get_current_user(self):
        """Override to determine the current user from, e.g., a cookie."""
        return None

    def render(self, **kwargs):
        return self.render_http('%s' % (self._payload['status_msg']), {})
    
    http_format = "HTTP/1.1 %(code)s %(status)s\r\n%(headers)s\r\n\r\n%(body)s"
    def render_http(self, body, headers, http_200=False, **kwargs):
        """Renders payload and prepares HTTP response.

        Allows forcing HTTP status to be 200 regardless of request status.
        """
        payload = dict(code=self.status_code,
                       status=self.status_msg,
                       body=body)
        if http_200:
            payload['code'] = 200
        headers['Content-Length'] = len(body)
        payload['headers'] = "\r\n".join('%s: %s' % (k,v)
                                         for k,v in headers.items())
        return self.http_format % payload    


class JSONRequest(WebRequestHandler):
    """JSONRequest is a system for maintaining a payload until the request is
    handled to completion. It offers rendering functions for printing the
    payload into JSON format.
    """

    def render(self, **kwargs):
        """Renders payload as json
        """
        return json.dumps(self._payload)
    

###
### Application logic
###

class Brubeck(object):
    def __init__(self, m2conn=None, request_handlers=None, pool=None,
                 *args, **kwargs):
        """Container for app details"""
        self.m2conn = m2conn
        self.request_handlers = request_handlers
        self.pool = pool
        if self.pool is None:
            self.pool = eventlet.GreenPool()

    def run(self):
        print 'Brubeck v0.1 online ]-----------------------------------'
        try:
            while True:
            #request = self.m2conn.recv()
            #self.pool.spawn_n(route_request, self, request)
                request = self.m2conn.recv()
                self.pool.spawn_n(route_request, self, request)
        except KeyboardInterrupt, ki:
            # Put a newline after ^C
            print '\nBrubeck going down...'

