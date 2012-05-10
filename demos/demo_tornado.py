#!/usr/bin/env python

from brubeck.request_handling import Brubeck
from brubeck.templating import TornadoRendering, load_tornado_env
from brubeck.connections import Mongrel2Connection
import sys

class DemoHandler(TornadoRendering):
    def get(self):
        name = self.get_argument('name', 'dude')
        context = {
            'name': name,
        }
        return self.render_template('success.html', **context)

app = Brubeck(msg_conn=Mongrel2Connection('tcp://127.0.0.1:9999', 'tcp://127.0.0.1:9998'),
              handler_tuples=[(r'^/brubeck', DemoHandler)],
              template_loader=load_tornado_env('./templates/tornado'))
app.run()
