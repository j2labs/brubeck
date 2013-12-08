from . import MessageHandler, MessageStatus
from . import render
from .. import messages

import Cookie
import logging


###
### Data Processing
###

HTTP_FORMAT = "HTTP/1.1 %(code)s %(status)s\r\n%(headers)s\r\n\r\n%(body)s"
HTTP_METHODS = ['get', 'post', 'put', 'delete', 'head', 'options', 'trace',
                'connect']


def http_render(body, status_code, status_msg, headers):
    """Renders arguments into an HTTP response.
    """
    payload = {'code': status_code, 'status': status_msg, 'body': body}
    content_length = 0
    if body is not None:
        content_length = len(messages.to_bytes(body))

    headers['Content-Length'] = content_length
    payload['headers'] = "\r\n".join('%s: %s' % (k, v)
                                     for k, v in headers.items())

    return HTTP_FORMAT % payload


###
### Cookies
###

def _lscmp(a, b):
    """Compares two strings in a cryptographically safe way
    """
    return not sum(0 if x == y else 1
                   for x, y in zip(a, b)) and len(a) == len(b)


def cookie_encode(data, key):
    """Encode and sign a pickle-able object. Return a (byte) string
    """
    msg = base64.b64encode(pickle.dumps(data, -1))
    sig = base64.b64encode(hmac.new(key, msg).digest())
    return messages.to_bytes('!') + sig + messages.to_bytes('?') + msg


def cookie_decode(data, key):
    """Verify and decode an encoded string. Return an object or None.
    """
    data = messages.to_bytes(data)
    if cookie_is_encoded(data):
        sig, msg = data.split(messages.to_bytes('?'), 1)
        if _lscmp(sig[1:], base64.b64encode(hmac.new(key, msg).digest())):
            return pickle.loads(base64.b64decode(msg))
    return None


def cookie_is_encoded(data):
    """Return True if the argument looks like a encoded cookie.
    """
    return bool(data.startswith(messages.to_bytes('!')) and \
                messages.to_bytes('?') in data)


###
### Handlers
###

class WebMessageHandler(MessageHandler):
    ### Message statuses
    SUCCESS_CODE = MessageStatus(200, 'OK')
    CREATED_CODE = MessageStatus(201, 'OK')
    MULTI_CODE = MessageStatus(207, 'Multi-status')
    FAILED_CODE = MessageStatus(400, 'Bad request')
    AUTH_FAILURE = MessageStatus(401, 'Authentication failed')
    FORBIDDEN = MessageStatus(403, 'Forbidden')
    NOT_FOUND =  MessageStatus(404, 'Not found')
    NOT_ALLOWED = MessageStatus(405, 'Method not allowed')
    SERVER_ERROR = MessageStatus(500, 'Server error')
    
    UPDATED_CODE = SUCCESS_CODE
    DEFAULT_STATUS = SERVER_ERROR 

    def initialize(self):
        """WebMessageHandler extends the payload for body and headers. It
        also provides both fields as properties to mask storage in payload
        """
        self.body = ''
        self.headers = dict()
        super(WebMessageHandler, self).initialize()

    def redirect(self, url):
        """Clears the payload before rendering the error status
        """
        logging.debug('Redirecting to url: %s' % url)
        self.clear_payload()
        self._finished = True
        msg = 'Page has moved to %s' % url
        self.set_status(302, status_msg=msg)
        self.headers['Location'] = '%s' % url
        return self.render()

    def options(self, *args, **kwargs):
        """Default to allowing all of the methods you have defined and public
        """
        self.headers["Access-Control-Allow-Methods"] = self.supported_methods
        self.set_status(200)
        return self.render()

    def unsupported(self, *args, **kwargs):
        def allow_header():
            methods = str.join(', ', map(str.upper, self.supported_methods))
            self.headers['Allow'] = methods
        return self.render_error(self.NOT_ALLOWED, error_handler=allow_header)

    def error(self, err):
        return self.render_error(self.SERVER_ERROR)

    @property
    def get_argument(self):
        return self.message.get_argument

    @property
    def get_arguments(self):
        return self.message.get_arguments

    @property
    def supported_methods(self):
        """List all the HTTP methods you have defined.
        """
        if not hasattr(self, "_supported_methods"):
            supported_methods = []
            for mef in HTTP_METHODS:
                if callable(getattr(self, mef, False)):
                    supported_methods.append(mef)
            self._supported_methods = supported_methods
        return self._supported_methods

    @property
    def cookies(self):
        if not hasattr(self, "_cookies"):
            self._cookies = Cookie.SimpleCookie()
        return self._cookies

    def get_cookie(self, key, default=None, secret=None):
        """Retrieve a cookie from message, if present, else fallback to
        `default` keyword. Accepts a secret key to validate signed cookies.
        """
        value = default
        if key in self.message.cookies:
            value = self.message.cookies[key].value
        if secret and value:
            dec = cookie_decode(value, secret)
            return dec[1] if dec and dec[0] == key else None
        return value

    def set_cookie(self, key, value, secret=None, **kwargs):
        """Add a cookie or overwrite an old one. If the `secret` parameter is
        set, create a `Signed Cookie` (described below).

        `key`: the name of the cookie.
        `value`: the value of the cookie.
        `secret`: required for signed cookies.

        params passed to as keywords:
          `max_age`: maximum age in seconds.
          `expires`: a datetime object or UNIX timestamp.
          `domain`: the domain that is allowed to read the cookie.
          `path`: limits the cookie to a given path

        If neither `expires` nor `max_age` are set (default), the cookie
        lasts only as long as the browser is not closed.
        """
        if secret:
            value = cookie_encode((key, value), secret)
        elif not isinstance(value, basestring):
            raise TypeError('Secret missing for non-string Cookie.')

        self.cookies[key] = value

        for k, v in kwargs.iteritems():
            self.cookies[key][k.replace('_', '-')] = v

    def delete_cookie(self, key, **kwargs):
        """Delete a cookie. Be sure to use the same `domain` and `path`
        parameters as used to create the cookie.
        """
        kwargs['max_age'] = -1
        kwargs['expires'] = 0
        self.set_cookie(key, '', **kwargs)

    def delete_cookies(self):
        """Deletes every cookie received from the user.
        """
        for key in self.message.cookies.iterkeys():
            self.delete_cookie(key)

    def render_cookies(self):
        """ Resolves cookies into multiline values.
        """
        cookie_vals = [c.OutputString() for c in self.cookies.values()]
        if len(cookie_vals) > 0:
            cookie_str = '\nSet-Cookie: '.join(cookie_vals)
            self.headers['Set-Cookie'] = cookie_str

    def render(self, body=None, headers=None, status=None):
        self.body = body if body else self.body
        self.headers = headers if headers else self.headers
        self.status = status if status else self.SUCCESS_CODE
        self.render_cookies()

        response = render(self.body, self.status, self.headers)

        logging.info('%s %s %s (%s)' % (self.status.code,
                                        self.message.method,
                                        self.message.path,
                                        self.message.remote_addr))
        return response


class JSONMessageHandler(WebMessageHandler):
    """This class is virtually the same as the WebMessageHandler with a slight
    change to how payloads are handled to make them more appropriate for
    representing JSON transmissions.

    The `hide_status` flag is used to reduce the payload down to just the data.
    """
    def render(self, status_code=None, hide_status=False, **kwargs):
        if status_code:
            self.set_status(status_code)

        self.render_cookies()

        self.headers['Content-Type'] = 'application/json'

        if hide_status and 'data' in self._payload:
            body = json.dumps(self._payload['data'])
        else:
            body = json.dumps(self._payload)

        response = render(body, self.status_code, self.status_msg,
                          self.headers)

        logging.info('%s %s %s (%s)' % (self.status_code, self.message.method,
                                        self.message.path,
                                        self.message.remote_addr))
        return response
