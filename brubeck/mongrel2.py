from .request_handling import zmq

import ujson as json
from uuid import uuid4
import cgi
import re
import logging
import Cookie

from request import to_bytes, to_unicode, parse_netstring

###
### Request handling code
###

###
### Mongrel2 handling code
###

CTX = zmq.Context()
MAX_IDENTS = 100


class Mongrel2Connection(object):
    """This class is an abstraction for how Brubeck sends and receives
    messages. This abstraction makes it possible for something other than
    Mongrel2 to be used easily.
    """

    def __init__(self, pull_addr, pub_addr):
        """sender_id = uuid.uuid4() or anything unique
        pull_addr = pull socket used for incoming messages
        pub_addr = publish socket used for outgoing messages

        The class encapsulates socket type by referring to it's pull socket
        as in_sock and it's publish socket as out_sock.
        """

        # Each Brubeck instance uniquely identifies itself. Mongrel2 requires
        # this for the request handler's pub socket as a subscriber id.
        self.sender_id = uuid4().hex

        in_sock = CTX.socket(zmq.PULL)
        in_sock.connect(pull_addr)

        out_sock = CTX.socket(zmq.PUB)
        out_sock.setsockopt(zmq.IDENTITY, self.sender_id)
        out_sock.connect(pub_addr)

        self.in_addr = pull_addr
        self.out_addr = pub_addr
        self.in_sock = in_sock
        self.out_sock = out_sock

    def recv(self):
        """Receives a raw mongrel2.handler.Request object that you
        can then work with.
        """
        msg = self.in_sock.recv()
        req = Request.parse_msg(msg)
        return req

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
