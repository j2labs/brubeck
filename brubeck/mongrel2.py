from eventlet.green import zmq
import json
from uuid import uuid4
import cgi
import re
import logging
import Cookie


###
### Request handling code
###

def parse_netstring(ns):
    len, rest = ns.split(':', 1)
    len = int(len)
    assert rest[len] == ',', "Netstring did not end in ','"
    return rest[:len], rest[len+1:]

def to_bytes(data, enc='utf8'):
    """Convert anything to bytes
    """
    return data.encode(enc) if isinstance(data, unicode) else bytes(data)


class Request(object):

    def __init__(self, sender, conn_id, path, headers, body,
                 *args, **kwargs):
        self.sender = sender
        self.path = path
        self.conn_id = conn_id
        self.headers = headers
        self.body = body

        if self.headers['METHOD'] == 'JSON':
            self.data = json.loads(body)
        else:
            self.data = {}


        # populate arguments with QUERY string
        self.arguments = {}
        if 'QUERY' in self.headers:
            query = self.headers['QUERY']
            arguments = cgi.parse_qs(query)
            for name, values in arguments.iteritems():
                values = [v for v in values if v]
                if values: self.arguments[name] = values

        # handle data, multipart or not
        if self.method in ("POST", "PUT") and self.content_type:
            form_encoding = "application/x-www-form-urlencoded"
            if self.content_type.startswith(form_encoding):
                arguments = cgi.parse_qs(self.body)
                for name, values in arguments.iteritems():
                    values = [v for v in values if v]
                    if values:
                        self.arguments.setdefault(name, []).extend(values)
            # Not ready for this, but soon
#            elif content_type.startswith("multipart/form-data"):
#                fields = content_type.split(";")
#                for field in fields:
#                    k, sep, v = field.strip().partition("=")
#                    if k == "boundary" and v:
#                        self._parse_mime_body(v, data)
#                        break
#                else:
#                    logging.warning("Invalid multipart/form-data")

    @property
    def method(self):
        return self.headers.get('METHOD')

    @property
    def content_type(self):
        return self.headers.get("content-type")

    @property
    def version(self):
        return self.headers.get('VERSION')

    @property
    def cookies(self):
        """Lazy generation of cookies from request headers."""
        if not hasattr(self, "_cookies"):
            self._cookies = Cookie.SimpleCookie()
            if "cookie" in self.headers:
                try:
                    cookies = self.headers['cookie']
                    self._cookies.load(to_bytes(cookies))
                except Exception, e:
                    logging.error('Failed to load cookies')
                    self.clear_all_cookies()
        return self._cookies

    @staticmethod
    def parse_msg(msg):
        """Static method for constructing a Request instance out of a
        message read straight off a zmq socket.
        """
        sender, conn_id, path, rest = msg.split(' ', 3)
        headers, rest = parse_netstring(rest)
        body, _ = parse_netstring(rest)
        headers = json.loads(headers)

        return Request(sender, conn_id, path, headers, body)

    def is_disconnect(self):
        if self.headers.get('METHOD') == 'JSON':
            logging.error('DISCONNECT')
            return self.data.get('type') == 'disconnect'

    def should_close(self):
        """Determines if Request data matches criteria for closing request"""
        if self.headers.get('connection') == 'close':
            return True
        elif self.headers.get('VERSION') == 'HTTP/1.0':
            return True
        else:
            return False

    def get_arguments(self, name, strip=True):
        """Returns a list of the arguments with the given name. If the argument
        is not present, returns a None. The returned values are always unicode.
        """
        values = self.arguments.get(name, None)
        if values is None:
            return None

        # Get the stripper ready
        if strip:
            stripper = lambda v: v.strip()
        else:
            stripper = lambda v: v

        def clean_value(v):
            v = re.sub(r"[\x00-\x08\x0e-\x1f]", " ", v)
            v = unicode(v)
            v = stripper(v)
            return v

        values = [clean_value(v) for v in values]
        return values

    def get_argument(self, name, default=None, strip=True):
        """Returns the value of the argument with the given name.

        If the argument appears in the url more than once, we return the
        last value.
        """
        args = self.get_arguments(name, strip=strip)
        if not args:
            return default
        return args[-1]


###
### Mongrel2 handling code
###

CTX = zmq.Context()
MAX_IDENTS = 100

class Mongrel2Connection(object):

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

