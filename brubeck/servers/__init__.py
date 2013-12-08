from .. import concurrency
from .. import version
from .. import handlers
from ..plugins import Pluggable
from ..messages import to_bytes, to_unicode

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

import ujson as json


###
### Application logic
###

class Server(object, Pluggable):

    def __init__(self, msg_conn=None, handlers=None, pool=None,
                 default_handler=None, log_level=logging.INFO, db=None,
                 plugins=None, *args, **kwargs):
        
        logging.basicConfig(level=log_level)
        logging.info('Using coroutine library: %s' % concurrency.CORO_LIBRARY)

        if msg_conn is not None:
            self.msg_conn = msg_conn
        else:
            raise ValueError('No message connection provided.')

        if handlers is not None:
            self.init_routes(handlers)

        self.pool = pool
        if not pool:
            self.pool = concurrency.init_pool()

        self.default_handler = default_handler
        if self.default_handler is None:
            self.default_handler = handlers.MessageHandler

        self.db = db

        if plugins:
            map(self.activate_plugin, plugins)

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
                    return self.default_handler(app, msg).unsupported()
                else:
                    return kallable(app, msg, *args)

            self.add_route_rule(url_pattern, check_method)
            return check_method
        return decorator

    def route_message(self, message):
        handler = None
        for (regex, kallable) in self._routes:
            route_check = regex.match(message.path)

            if route_check:
                route_args = route_check.groupdict() or route_check.groups() or []

                if inspect.isclass(kallable):
                    handler = kallable(self, message)
                    handler._args = route_args
                    return handler
                else:
                    if isinstance(route_args, dict):
                        kwargs = dict((k, v) for k, v in route_args.items() if v)
                        handler = lambda: kallable(self, message, **kwargs)
                    else:
                        handler = lambda: kallable(self, message, *route_args)
                    return handler

        if handler is None:
            handler = self.default_handler(self, message)

        return handler

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


class WebServer(Server):
    def __init__(self, cookie_secret=None, login_route=None, **kw):
        self.cookie_secret = cookie_secret
        self.login_route = login_route
        super(WebServer, self).__init__(**kw)
