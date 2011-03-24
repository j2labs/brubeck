#!/usr/bin/env python

import sys

from brubeck.request_handling import Brubeck, WebMessageHandler
from brubeck.templating import Jinja2Rendering, load_jinja2_env

class DemoHandler(WebMessageHandler, Jinja2Rendering):
    def get(self):
        name = self.get_argument('name', 'whomever you are')
        context = {
            'name': name,
        }
        return self.render_template('success.html', **context)

config = {
    'handler_tuples': [(r'^/brubeck', DemoHandler)],
    'template_loader': load_jinja2_env('./templates/jinja2'),
}

app = Brubeck(('ipc://127.0.0.1:9999', 'ipc://127.0.0.1:9998'), **config)
app.run()
