from . import concurrency
from . import version
from .handlers import WebMessageHandler, render

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
from messages import to_bytes, to_unicode

import ujson as json


###
### Application logic
###

class Brubeck(object):

    MULTIPLE_ITEM_SEP = ','

    def __init__(self, msg_conn=None, handler_tuples=None, pool=None,
                 base_handler=None, log_level=logging.INFO, login_route=None,
                 db_conn=None, cookie_secret=None, *args, **kwargs):
        """
        Brubeck is a class for managing connections to servers. It
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

        `log_level` is a log level mapping to Python's `logging` module's
        levels.

        `login_route` is the default route for a login operation.

        `db_conn` is a database connection to be shared in this process

        `cookie_secret` is a string to use for signing secure cookies.
        """
        logging.basicConfig(level=log_level)
        logging.info('Using coroutine library: %s' % concurrency.CORO_LIBRARY)

        if msg_conn is not None:
            self.msg_conn = msg_conn
        else:
            raise ValueError('No message connection provided.')

        self.handler_tuples = handler_tuples
        if self.handler_tuples is not None:
            self.init_routes(handler_tuples)

        self.pool = concurrency.init_pool()

        self.base_handler = base_handler
        if self.base_handler is None:
            self.base_handler = WebMessageHandler

        self.db_conn = db_conn

        self.login_route = login_route

        # This must be set to use secure cookies
        self.cookie_secret = cookie_secret

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
                url_args = url_check.groupdict() or url_check.groups() or []

                if inspect.isclass(kallable):
                    handler = kallable(self, message)
                    handler._args = url_args
                    return handler
                else:
                    if isinstance(url_args, dict):
                        kwargs = dict((k, v) for k, v in url_args.items() if v)
                        handler = lambda: kallable(self, message, **kwargs)
                    else:
                        handler = lambda: kallable(self, message, *url_args)
                    return handler

        if handler is None:
            handler = self.base_handler(self, message)

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
