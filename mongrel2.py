from eventlet.green import zmq
import time
import json


###
### Request handling code
###

def parse_netstring(ns):
    len, rest = ns.split(':', 1)
    len = int(len)
    assert rest[len] == ',', "Netstring did not end in ','"
    return rest[:len], rest[len+1:]


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

    @property
    def method(self):
        return self.headers.get('METHOD')

    @property
    def version(self):
        return self.headers.get('VERSION')

    @staticmethod
    def parse_msg(msg):
        """Static method for constructing a Request instance out of a
        message read straight of a zmq socket.
        """
        sender, conn_id, path, rest = msg.split(' ', 3)
        headers, rest = parse_netstring(rest)
        body, _ = parse_netstring(rest)

        headers = json.loads(headers)

        return Request(sender, conn_id, path, headers, body)

    def is_disconnect(self):
        if self.headers.get('METHOD') == 'JSON':
            return self.data['type'] == 'disconnect'

    def should_close(self):
        """Determines if Request data matches criteria for closing request"""
        if self.headers.get('connection') == 'close':
            return True
        elif self.headers.get('VERSION') == 'HTTP/1.0':
            return True
        else:
            return False


###
### Http handling code
###

CTX = zmq.Context()

HTTP_FORMAT = "HTTP/1.1 %(code)s %(status)s\r\n%(headers)s\r\n\r\n%(body)s"
MAX_IDENTS = 100

def http_response(body, code, status, headers):
    payload = {'code': code, 'status': status, 'body': body}
    headers['Content-Length'] = len(body)
    payload['headers'] = "\r\n".join('%s: %s' % (k,v) for k,v in
                                     headers.items())

    return HTTP_FORMAT % payload


class Mongrel2Connection(object):

    def __init__(self, sender_id, pull_addr, pub_addr):
        """sender_id = uuid.uuid1() or anything unique
        pull_addr = pull socket used for incoming messages
        pub_addr = publish socket used for outgoing messages

        The class encapsulates socket tupe by referring to it's pull socket
        as in_sock and it's publish socket as out_sock.
        """
        self.sender_id = sender_id

        in_sock = CTX.socket(zmq.PULL)
        in_sock.connect(pull_addr)

        out_sock = CTX.socket(zmq.PUB)
        out_sock.setsockopt(zmq.IDENTITY, sender_id)
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
        #self.out_sock.send_pyobj(header + ' ' + msg)
        self.out_sock.send(header + ' ' + msg)

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

