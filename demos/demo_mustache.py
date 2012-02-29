#!/usr/bin/env python

from brubeck.request_handling import Brubeck
from brubeck.templating import MustacheRendering, load_mustache_env

class DemoHandler(MustacheRendering):
    def get(self):
        name = self.get_argument('name', 'dude')
        context = {
            'name': name,
        }
        return self.render_template('success', **context)

app = Brubeck(mongrel2_pair=('ipc://127.0.0.1:9999', 'ipc://127.0.0.1:9998'),
              handler_tuples=[(r'^/brubeck', DemoHandler)],
              template_loader=load_mustache_env('./templates/mustache'))
app.run()
