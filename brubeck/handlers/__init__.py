from .. import messages

import time
import logging
from collections import namedtuple


###
### Data Processing
###

def render(body, status, headers):
    """In it's most basic form, a message is rendered a dict with four keys.
    These keys are expected to exist in any rendered form of a message, but
    more keys can be added as necessary.
    """
    payload = {
        'body': body,
        'status_code': status.code,
        'status_msg': status.msg,
        'headers': headers,
    }
    return payload

MessageStatus = namedtuple('HandlerResponse', ['code', 'msg'], verbose=False)


###
### Handlers
###

class MessageHandler(object):
    ### Message statuses
    SUCCESS_CODE = MessageStatus(0, 'OK')
    BAD_REQUEST = MessageStatus(-1, 'Bad request')
    AUTH_FAILURE = MessageStatus(-2, 'Authentication failed')
    NOT_FOUND = MessageStatus(-3, 'Not found')
    NOT_ALLOWED = MessageStatus(-4, 'Method not allowed')
    SERVER_ERROR = MessageStatus(-5, 'Server error')
    
    DEFAULT_STATUS = SERVER_ERROR

    def __init__(self, application, message, *args, **kwargs):
        """A MessageHandler is called at two major points, with regard to the
        eventlet scheduler. __init__ is the first point, which is responsible
        for bootstrapping the state of a single handler.

        __call__ is the second major point.
        """
        self.application = application
        self.message = message
        self._finished = False
        self.initialize()

    def initialize(self, status=None):
        """Hook for subclass. Implementers should be aware that this class's
        __init__ calls initialize.
        """
        self.status = status if status else self.DEFAULT_STATUS
        self.timestamp = int(time.time() * 1000)

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

    def unsupported(self):
        """Called anytime an unsupported request is made.
        """
        return self.render_error(self.SERVER_ERROR)

    def error(self, err):
        return self.unsupported()

    @property
    def db(self):
        """Short hand to put database connection in easy reach of handlers
        """
        return self.application.db

    @property
    def plugins(self):
        """Short hand to make the plugins easy to reach
        """
        return self.application.plugins

    @property
    def supported_methods(self):
        """List all the methods you have defined.
        """
        pass

    def render(self, status=None, hide_status=False, **kwargs):
        """Renders entire payload as json dump. Subclass and overwrite this
        function if a different output format is needed. See WebMessageHandler
        as an example.
        """
        self.status = status if status else self.status
        rendered = json.dumps(self._payload)
        return rendered

    def render_error(self, status, error_handler=None, **kwargs):
        """Clears the payload before rendering the error status.
        Takes a callable to perform customization before rendering the output.
        """
        if error_handler:
            error_handler()
        self._finished = True
        return self.render(status=status)

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
