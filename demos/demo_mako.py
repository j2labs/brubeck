#!/usr/bin/env python

import sys
from brubeck.request_handling import Brubeck, WebMessageHandler
from brubeck.templating import MakoRendering, load_mako_env


class DemoHandler(WebMessageHandler, MakoRendering):
  def get(self):
    name = self.get_argument('name', 'dude')
    context = {'name': name}
    return self.render_template('success.html', **context)


app = Brubeck(mongrel2_pair=('ipc://127.0.0.1:9999', 'ipc://127.0.0.1:9998'),
  handler_tuples=[(r'^/brubeck', DemoHandler)],
  template_loader=load_mako_env('./templates/mako'))
app.run()
