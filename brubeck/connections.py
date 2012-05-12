import ujson as json
from uuid import uuid4
import cgi
import re
import logging
import Cookie

from request import to_bytes, to_unicode, parse_netstring, Request


###
### Connection Classes
###

class Connection(object):
    """This class is an abstraction for how Brubeck sends and receives
    messages. The idea is that Brubeck waits to receive messages for some work
    and then it responds. Therefore each connection should essentially be a
    mechanism for reading a message and a mechanism for responding, if a
    response is necessary.
    """

    def __init__(self, incoming=None, outgoing=None):
        """The base `__init__()` function configures a unique ID and assigns
        the incoming and outgoing mechanisms to a name.

        `in_sock` and `out_sock` feel like misnomers at this time but they are
        preserved for a transition period.
        """
        self.sender_id = uuid4().hex
        self.in_sock = incoming
        self.out_sock = outgoing

    def _unsupported(self, name):
        """Simple function that raises an exception.
        """
        error_msg = 'Subclass of Connection has not implemented `%s()`' % name
        raise NotImplementedError(error_msg)


    def recv(self):
        """Receives a raw mongrel2.handler.Request object that you
        can then work with.
        """
        self._unsupported('recv')

    def _recv_forever_ever(self, fun_forever):
        """Calls a handler function that runs forever. The handler can be
        interrupted with a ctrl-c, though.
        """
        try:
            fun_forever()
        except KeyboardInterrupt, ki:
            # Put a newline after ^C
            print '\nBrubeck going down...'

    def send(self, uuid, conn_id, msg):
        """Function for sending a single message.
        """
        self._unsupported('send')
 
    def reply(self, req, msg):
        """Does a reply based on the given Request object and message.
        """
        self.send(req.sender, req.conn_id, msg)

    def reply_bulk(self, uuid, idents, data):
        """This lets you send a single message to many currently
        connected clients.  There's a MAX_IDENTS that you should
        not exceed, so chunk your targets as needed.  Each target
        will receive the message once by Mongrel2, but you don't have
        to loop which cuts down on reply volume.
        """
        self._unsupported('reply_bulk')
        self.send(uuid, ' '.join(idents), data)

    def close(self):
        """Close the connection.
        """
        self._unsupported('close')

    def close_bulk(self, uuid, idents):
        """Same as close but does it to a whole bunch of idents at a time.
        """
        self._unsupported('close_bulk')
        self.reply_bulk(uuid, idents, "")


###
### ZeroMQ
###

def load_zmq():
    """This function exists to determine where zmq should come from and then
    cache that decision at the module level.
    """
    if not hasattr(load_zmq, '_zmq'):
        from request_handling import CORO_LIBRARY
        if CORO_LIBRARY == 'gevent':
            from gevent_zeromq import zmq
        elif CORO_LIBRARY == 'eventlet':
            from eventlet.green import zmq
        load_zmq._zmq = zmq

    return load_zmq._zmq


def load_zmq_ctx():
    """This function exists to contain the namespace requirements of generating
    a zeromq context, while keeping the context at the module level. If other
    parts of the system need zeromq, they should use this function for access
    to the existing context.
    """
    if not hasattr(load_zmq_ctx, '_zmq_ctx'):
        zmq = load_zmq()
        zmq_ctx = zmq.Context()
        load_zmq_ctx._zmq_ctx = zmq_ctx
        
    return load_zmq_ctx._zmq_ctx


###
### Mongrel2
###

class Mongrel2Connection(Connection):
    """This class is an abstraction for how Brubeck sends and receives
    messages. This abstraction makes it possible for something other than
    Mongrel2 to be used easily.
    """
    MAX_IDENTS = 100

    def __init__(self, pull_addr, pub_addr):
        """sender_id = uuid.uuid4() or anything unique
        pull_addr = pull socket used for incoming messages
        pub_addr = publish socket used for outgoing messages

        The class encapsulates socket type by referring to it's pull socket
        as in_sock and it's publish socket as out_sock.
        """
        zmq = load_zmq()
        ctx = load_zmq_ctx()
        
        in_sock = ctx.socket(zmq.PULL)
        out_sock = ctx.socket(zmq.PUB)

        super(Mongrel2Connection, self).__init__(in_sock, out_sock)
        self.in_addr = pull_addr
        self.out_addr = pub_addr

        in_sock.connect(pull_addr)
        out_sock.setsockopt(zmq.IDENTITY, self.sender_id)
        out_sock.connect(pub_addr)

    def process_message(self, application, message):
        """This coroutine looks at the message, determines which handler will
        be used to process it, and then begins processing.
        
        The application is responsible for handling misconfigured routes.
        """
        request = Request.parse_msg(message)
        if request.is_disconnect():
            return  # Ignore disconnect msgs. Dont have areason to do otherwise
        handler = application.route_message(request)
        if callable(handler):
            response = handler()
        application.msg_conn.reply(request, response)

    def recv(self):
        """Receives a raw mongrel2.handler.Request object that you from the
        zeromq socket and return whatever is found.
        """
        zmq_msg = self.in_sock.recv()
        return zmq_msg

    def recv_forever_ever(self, application):
        """Defines a function that will run the primary connection Brubeck uses
        for incoming jobs. This function should then call super which runs the
        function in a try-except that can be ctrl-c'd.
        """
        def fun_forever():
            while True:
                request = self.recv()
                self.process_message(application, request)
        self._recv_forever_ever(fun_forever)

    def send(self, uuid, conn_id, msg):
        """Raw send to the given connection ID at the given uuid, mostly used
        internally.
        """
        header = "%s %d:%s," % (uuid, len(str(conn_id)), str(conn_id))
        self.out_sock.send(header + ' ' + to_bytes(msg))

    def reply(self, req, msg):
        """Does a reply based on the given Request object and message.
        """
        self.send(req.sender, req.conn_id, msg)

    def reply_bulk(self, uuid, idents, data):
        """This lets you send a single message to many currently
        connected clients.  There's a MAX_IDENTS that you should
        not exceed, so chunk your targets as needed.  Each target
        will receive the message once by Mongrel2, but you don't have
        to loop which cuts down on reply volume.
        """
        self.send(uuid, ' '.join(idents), data)

    def close(self):
        """Tells mongrel2 to explicitly close the HTTP connection.
        """
        pass

    def close_bulk(self, uuid, idents):
        """Same as close but does it to a whole bunch of idents at a time.
        """
        self.reply_bulk(uuid, idents, "")


###
### WSGI 
###

class WSGIConnection(Connection):
    """
    """

    def __init__(self, port=6767):
        super(WSGIConnection, self).__init__()
        self.port = port

    def process_message(self, application, environ, callback):
        request = Request.parse_wsgi_request(environ)
        handler = application.route_message(request)
        response = handler()
        x = callback(response['status'], response['headers'])
        return [str(response['body'])]

    def recv(self, environ, start_response):
        """Receives the request from the wsgi server."""
        setup_testing_defaults(environ)
        status = '200 OK'
        headers = [('Content-type', 'text/plain')]
        start_response(status, headers)
        ret = ["%s: %s\n" % (key, value)
               for key, value in environ.iteritems()]
        return ret 

    def recv_forever_ever(self, application):
        """Defines a function that will run the primary connection Brubeck uses
        for incoming jobs. This function should then call super which runs the
        function in a try-except that can be ctrl-c'd.
        """
        def fun_forever():
            from brubeck.request_handling import CORO_LIBRARY
            print "Serving on port %s..." % (self.port)

            def proc_msg(environ, callback):
                return self.process_message(application, environ, callback)
            
            if CORO_LIBRARY == 'gevent':
                from gevent import wsgi
                server = wsgi.WSGIServer(('', self.port), proc_msg)
                server.serve_forever()
                
            elif CORO_LIBRARY == 'eventlet':
                import eventlet
                server = eventlet.wsgi.server(eventlet.listen(('', self.port)),
                                              proc_msg)
                
        self._recv_forever_ever(fun_forever)

        
