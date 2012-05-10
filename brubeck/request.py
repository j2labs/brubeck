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
            elif self.content_type.startswith("multipart/form-data"):
                fields = self.content_type.split(";")
                for field in fields:
                    k, sep, v = field.strip().partition("=")
                    if k == "boundary" and v:
                        self.arguments = {}
                        self.files = {}
                        self._parse_mime_body(v, self.body, self.arguments,
                                              self.files)
                        break
                else:
                    logging.warning("Invalid multipart/form-data")

    def _parse_mime_body(self, boundary, data, arguments, files):
        if boundary.startswith('"') and boundary.endswith('"'):
            boundary = boundary[1:-1]
        if data.endswith("\r\n"):
            footer_length = len(boundary) + 6 
        else:
            footer_length = len(boundary) + 4
        data = str(data)
        parts = data[:-footer_length].split("--" + str(boundary) + "\r\n")
        for part in parts:
            if not part:
                continue
            eoh = part.find("\r\n\r\n")
            if eoh == -1: 
                logging.warning("multipart/form-data missing headers")
                continue
            #headers = HTTPHeaders.parse(part[:eoh].decode("utf-8"))
            header_string = part[:eoh].decode("utf-8")
            headers = dict()
            last_key = ''
            for line in header_string.splitlines():
                if line[0].isspace():
                    # continuation of a multi-line header
                    new_part = ' ' + line.lstrip()
                    headers[last_key] += new_part
                else:
                    name, value = line.split(":", 1)
                    last_key = "-".join([w.capitalize() for w in name.split("-")])
                    headers[name] = value.strip()
    
            disp_header = headers.get("Content-Disposition", "") 
            disposition, disp_params = self._parse_header(disp_header)
            if disposition != "form-data" or not part.endswith("\r\n"):
                logging.warning("Invalid multipart/form-data")
                continue
            value = part[eoh + 4:-2]
            if not disp_params.get("name"):
                logging.warning("multipart/form-data value missing name")
                continue
            name = disp_params["name"]
            if disp_params.get("filename"):
                ctype = headers.get("Content-Type", "application/unknown")
                files.setdefault(name, []).append(dict(
                    filename=disp_params["filename"], body=value,
                    content_type=ctype))
            else:
                arguments.setdefault(name, []).append(value)

    def _parseparam(self, s):
        while s[:1] == ';':
            s = s[1:]
            end = s.find(';')
            while end > 0 and (s.count('"', 0, end) - s.count('\\"', 0, end)) % 2:
                end = s.find(';', end + 1)
            if end < 0:
                end = len(s)
            f = s[:end]
            yield f.strip()
            s = s[end:]

    def _parse_header(self, line):
        """Parse a Content-type like header.
            
        Return the main content-type and a dictionary of options.
        """
        parts = self._parseparam(';' + line)
        key = parts.next()
        pdict = {}
        for p in parts:
            i = p.find('=')
            if i >= 0:
                name = p[:i].strip().lower()
                value = p[i + 1:].strip()
                if len(value) >= 2 and value[0] == value[-1] == '"':
                    value = value[1:-1]
                    value = value.replace('\\\\', '\\').replace('\\"', '"')
                pdict[name] = value
        return key, pdict    

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
