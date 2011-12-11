#!/usr/bin/env python


from brubeck.request_handling import Brubeck, WebMessageHandler
from brubeck.templating import load_jinja2_env, Jinja2Rendering
import sys
import datetime
import time

try:
    import eventlet
except:
    import gevent

class DemoHandler(Jinja2Rendering):
    def get(self):
        name = self.get_argument('name', 'dude')
        self.set_body('Take five, %s!' % name)
        return self.render_template('base.html')


class FeedHandler(WebMessageHandler):
    def get(self):
        try:
            eventlet.sleep(5) # simple way to demo long polling :)
        except:
            gevent.sleep(5)
        self.set_body('The current time is: %s' % datetime.datetime.now(),
                      headers={'Content-Type': 'text/plain'})
        return self.render()


config = {
    'mongrel2_pair': ('ipc://127.0.0.1:9999', 'ipc://127.0.0.1:9998'),
    'handler_tuples': [(r'^/$', DemoHandler),
                       (r'^/feed', FeedHandler)],
    'template_loader': load_jinja2_env('./templates/longpolling'),
}


app = Brubeck(**config)
app.run()
