import time
import logging
import Cookie


###
### Result Processing
###

def render(body, status_code, status_msg, headers):
    payload = {
        'body': body,
        'status_code': status_code,
        'status_msg': status_msg,
        'headers': headers,
    }
    return payload


###
### Handlers
###

class MessageHandler(object):
    """The base class for request handling. It's functionality consists
    primarily of a payload system and a way to store some state for
    the duration of processing the message.

    Mixins are provided in Brubeck's modules for extending these handlers.
    Mixins provide a simple way to add functions to a MessageHandler that are
    unique to the message our handler is designed for. Mix in logic as you
    realize you need it. Or rip it out. Keep your handlers lean.

    Two callbacks are offered for state preparation.

    The `initialize` function allows users to add steps to object
    initialization. A mixin, however, should never use this. You could hook
    the request handler up to a database connection pool, for example.

    The `prepare` function is called just before any decorators are called.
    The idea here is to give Mixin creators a chance to build decorators that
    depend on post-initialization processing to have taken place. You could use
    that database connection we created in `initialize` to check the username
    and password from a user.
    """
    _SUCCESS_CODE = 0
    _BAD_REQUEST = -1
    _AUTH_FAILURE = -2
    _NOT_FOUND = -3
    _NOT_ALLOWED = -4
    _SERVER_ERROR = -5
    _DEFAULT_STATUS = _SERVER_ERROR
    
    _response_codes = {
        0: 'OK',
        -1: 'Bad request',
        -2: 'Authentication failed',
        -3: 'Not found',
        -4: 'Method not allowed',
        -5: 'Server error',
    }

    ### Payload keys
    _STATUS_CODE = 'status_code'
    _STATUS_MSG = 'status_msg'
    _TIMESTAMP = 'timestamp'

    def __init__(self, application, message, *args, **kwargs):
        """A MessageHandler is called at two major points, with regard to the
        eventlet scheduler. __init__ is the first point, which is responsible
        for bootstrapping the state of a single handler.

        __call__ is the second major point.
        """
        self.application = application
        self.message = message
        self._payload = dict()
        self._finished = False
        self.set_status(self._DEFAULT_STATUS)
        self.set_timestamp(int(time.time() * 1000))
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

    def on_finish(self):
        """Called after the message handling method. Counterpart to prepare
        """
        pass

    @property
    def db_conn(self):
        """Short hand to put database connection in easy reach of handlers
        """
        return self.application.db_conn

    @property
    def supported_methods(self):
        """List all the methods you have defined.
        """
        pass

    def unsupported(self):
        """Called anytime an unsupported request is made.
        """
        return self.render_error(-1)

    def error(self, err):
        return self.unsupported()

    def add_to_payload(self, key, value):
        """Upserts key-value pair into payload.
        """
        self._payload[key] = value

    def clear_payload(self):
        """Resets the payload but preserves the current status_code.
        """
        status_code = self.status_code
        self._payload = dict()
        self.set_status(status_code)
        self.initialize()

    def set_status(self, status_code):
        """Sets the status code of the payload to <status_code> and sets
        status msg to the the relevant msg as defined in _response_codes.
        """
        status_msg = self._response_codes.get(status_code, str(status_code))
        self.add_to_payload(self._STATUS_CODE, status_code)
        self.add_to_payload(self._STATUS_MSG, status_msg)

    @property
    def status_code(self):
        return self._payload[self._STATUS_CODE]

    @property
    def status_msg(self):
        return self._payload[self._STATUS_MSG]

    @property
    def current_time(self):
        return self._payload[self._TIMESTAMP]

    def set_timestamp(self, timestamp):
        """Sets the timestamp to given timestamp.
        """
        self.add_to_payload(self._TIMESTAMP, timestamp)
        self.timestamp = timestamp

    def render(self, status_code=None, hide_status=False, **kwargs):
        """Renders entire payload as json dump. Subclass and overwrite this
        function if a different output format is needed. See WebMessageHandler
        as an example.
        """
        if not status_code:
            status_code = self.status_code
        self.set_status(status_code)
        rendered = json.dumps(self._payload)
        return rendered

    def render_error(self, status_code, error_handler=None, **kwargs):
        """Clears the payload before rendering the error status.
        Takes a callable to perform customization before rendering the output.
        """
        self.clear_payload()
        if error_handler:
            error_handler()
        self._finished = True
        return self.render(status_code=status_code)

    def __call__(self):
        """This function handles mapping the request type to a function on
        the request handler.

        It requires a method attribute to indicate which function on the
        handler should be called. If that function is not supported, call the
        handlers unsupported function.

        In the event that an error has already occurred, _finished will be
        set to true before this function call indicating we should render
        the handler and nothing else.

        In all cases, generating a response for mongrel2 is attempted.
        """
        try:
            self.prepare()
            if not self._finished:
                mef = self.message.method.lower()  # M-E-T-H-O-D man!

                # Find function mapped to method on self
                if mef in self.supported_methods:
                    fun = getattr(self, mef, self.unsupported)
                else:
                    fun = self.unsupported

                # Call the function we settled on
                try:
                    if not hasattr(self, '_args') or self._args is None:
                        self._args = []

                    if isinstance(self._args, dict):
                        ### if the value was optional and not included, filter it
                        ### out so the functions default takes priority
                        kwargs = dict((k, v)
                                      for k, v in self._args.items() if v)
                        rendered = fun(**kwargs)
                    else:
                        rendered = fun(*self._args)

                    if rendered is None:
                        logging.debug('Handler had no return value: %s' % fun)
                        return ''
                except Exception, e:
                    logging.error(e, exc_info=True)
                    rendered = self.error(e)

                self._finished = True
                return rendered
            else:
                return self.render()
        finally:
            self.on_finish()


###
### Web Message Handling
###

HTTP_FORMAT = "HTTP/1.1 %(code)s %(status)s\r\n%(headers)s\r\n\r\n%(body)s"
HTTP_METHODS = ['get', 'post', 'put', 'delete', 'head', 'options', 'trace',
                'connect']


def http_response(body, code, status, headers):
    """Renders arguments into an HTTP response.
    """
    payload = {'code': code, 'status': status, 'body': body}
    content_length = 0
    if body is not None:
        content_length = len(to_bytes(body))

    headers['Content-Length'] = content_length
    payload['headers'] = "\r\n".join('%s: %s' % (k, v)
                                     for k, v in headers.items())

    return HTTP_FORMAT % payload


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
    return to_bytes('!') + sig + to_bytes('?') + msg


def cookie_decode(data, key):
    ''' Verify and decode an encoded string. Return an object or None.'''
    data = to_bytes(data)
    if cookie_is_encoded(data):
        sig, msg = data.split(to_bytes('?'), 1)
        if _lscmp(sig[1:], base64.b64encode(hmac.new(key, msg).digest())):
            return pickle.loads(base64.b64decode(msg))
    return None


def cookie_is_encoded(data):
    ''' Return True if the argument looks like a encoded cookie.'''
    return bool(data.startswith(to_bytes('!')) and to_bytes('?') in data)


class WebMessageHandler(MessageHandler):
    """A base class for common functionality in a request handler.

    Tornado's design inspired this design.
    """
    _SUCCESS_CODE = 200
    _UPDATED_CODE = 200
    _CREATED_CODE = 201
    _MULTI_CODE = 207
    _FAILED_CODE = 400
    _AUTH_FAILURE = 401
    _FORBIDDEN = 403
    _NOT_FOUND = 404
    _NOT_ALLOWED = 405
    _SERVER_ERROR = 500
    _DEFAULT_STATUS = _SERVER_ERROR    

    _response_codes = {
        200: 'OK',
        400: 'Bad request',
        401: 'Authentication failed',
        403: 'Forbidden',
        404: 'Not found',
        405: 'Method not allowed',
        500: 'Server error',
    }

    ### Payload keys
    _HEADERS = 'headers'

    def initialize(self):
        """WebMessageHandler extends the payload for body and headers. It
        also provides both fields as properties to mask storage in payload
        """
        self.body = ''
        self.headers = dict()

    def set_body(self, body, headers=None, status_code=_SUCCESS_CODE):
        """
        """
        self.body = body
        self.set_status(status_code)
        if headers is not None:
            self.headers = headers

    @property
    def supported_methods(self):
        """List all the HTTP methods you have defined.
        """
        supported_methods = []
        for mef in HTTP_METHODS:
            if callable(getattr(self, mef, False)):
                supported_methods.append(mef)
        return supported_methods

    ### Rendering Functions
    
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
        return self.render_error(self._NOT_ALLOWED, error_handler=allow_header)

    def error(self, err):
        self.render_error(self._SERVER_ERROR)

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

    def get_argument(self, name, default=None, strip=True):
        """
        Returns the value of the argument with the given name.

        If the argument appears in the url more than once, we return the
        last value.
        """
        return self.message.get_argument(name, default=default, strip=strip)

    def get_arguments(self, name, strip=True):
        """
        Returns a list of the arguments with the given name.
        """
        return self.message.get_arguments(name, strip=strip)

    ### Cookies

    def get_cookie(self, key, default=None, secret=None):
        """
        Retrieve a cookie from message, if present, else fallback to
        `default` keyword. Accepts a secret key to validate signed cookies.
        """
        value = default
        if key in self.message.cookies:
            value = self.message.cookies[key].value
        if secret and value:
            dec = cookie_decode(value, secret)
            return dec[1] if dec and dec[0] == key else None
        return value

    @property
    def cookies(self):
        """
        Lazy creation of response cookies.
        """
        if not hasattr(self, "_cookies"):
            self._cookies = Cookie.SimpleCookie()
        return self._cookies

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

        # Set cookie value
        self.cookies[key] = value

        # handle keywords
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

    ### Rendering

    def render_cookies(self):
        """ Resolves cookies into multiline values.
        """
        cookie_vals = [c.OutputString() for c in self.cookies.values()]
        if len(cookie_vals) > 0:
            cookie_str = '\nSet-Cookie: '.join(cookie_vals)
            self.headers['Set-Cookie'] = cookie_str

    def render(self, status_code=None, http_200=False, **kwargs):
        """Renders payload and prepares the payload for a successful HTTP
        response.

        Allows forcing HTTP status to be 200 regardless of request status
        for cases where payload contains status information.
        """
        if status_code:
            self.set_status(status_code)

        # Some API's send error messages in the payload rather than over
        # HTTP. Not necessarily ideal, but supported.
        status_code = self.status_code
        if http_200:
            status_code = 200

        self.render_cookies()

        response = render(self.body, status_code, self.status_msg, self.headers)

        logging.info('%s %s %s (%s)' % (status_code, self.message.method,
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
