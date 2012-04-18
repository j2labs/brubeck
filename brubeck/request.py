import cgi
import json
import Cookie
import logging
import re

def parse_netstring(ns):
    length, rest = ns.split(':', 1)
    length = int(length)
    assert rest[length] == ',', "Netstring did not end in ','"
    return rest[:length], rest[length + 1:]

def to_bytes(data, enc='utf8'):
    """Convert anything to bytes
    """
    return data.encode(enc) if isinstance(data, unicode) else bytes(data)


def to_unicode(s, enc='utf8'):
    """Convert anything to unicode
    """
    return s if isinstance(s, unicode) else unicode(str(s), encoding=enc)


class Request(object):
    """Word.
    """
    def __init__(self, sender, conn_id, path, headers, body, *args, **kwargs):
        self.sender = sender
        self.path = path
        self.conn_id = conn_id
        self.headers = headers
        self.body = body

        if self.method == 'JSON':
            self.data = json.loads(body)
        else:
            self.data = {}

        ### populate arguments with QUERY string
        self.arguments = {}
        if 'QUERY' in self.headers:
            query = self.headers['QUERY']
            arguments = cgi.parse_qs(query.encode("utf-8"))
            for name, values in arguments.iteritems():
                values = [v for v in values if v]
                if values:
                    self.arguments[name] = values

        ### handle data, multipart or not
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
    def remote_addr(self):
        return self.headers.get('x-forwarded-for')

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
        r = Request(sender, conn_id, path, headers, body)
        r.is_wsgi = False
        return r

    @staticmethod
    def parse_wsgi_request(environ):
        """Static method for constructing Request instance out of environ
        dict from wsgi server."""
        conn_id = None
        sender = "WSGI_server"
        path = environ['PATH_INFO']
        body = ""
        if "CONTENT_LENGTH" in environ and environ["CONTENT_LENGTH"]:
            body = environ["wsgi.input"].read(int(environ['CONTENT_LENGTH']))
            del environ["CONTENT_LENGTH"]
            del environ["wsgi.input"]
        #setting headers to environ dict with no manipulation
        headers = environ
        # normalize request dict
        if 'REQUEST_METHOD' in headers:
            headers['METHOD'] = headers['REQUEST_METHOD']
        if 'QUERY_STRING' in headers:
            headers['QUERY'] = headers['QUERY_STRING']
        if 'CONTENT_TYPE' in headers:
            headers['content-type'] = headers['CONTENT_TYPE']
        headers['version'] = 1.1  #TODO: hardcoded!
        if 'HTTP_COOKIE' in headers:
            headers['cookie'] = headers['HTTP_COOKIE']
        if 'HTTP_CONNECTION' in headers:
            headers['connection'] = headers['HTTP_CONNECTION']
        r = Request(sender, conn_id, path, headers, body)
        r.is_wsgi = True
        return r

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
            v = to_unicode(v)
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
