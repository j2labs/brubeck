#!/usr/bin/env python


"""This is a rough prototype
"""

import sys

from brubeck.request_handling import Brubeck, WebMessageHandler
from brubeck.templating import Jinja2Rendering, load_jinja2_env

import logging
logging.basicConfig(**{'level': logging.DEBUG})

class DemoHandler(WebMessageHandler, Jinja2Rendering):
    def get(self):
        """Function called for HTTP GET"""
        logging.debug('DemoHandler.get() called')
        name = self.get_argument('name', 'whomever you are')
        context = {
            'name': name,
        }
        return self.render_template('success.html', **context)

        
if __name__ == '__main__':
    pull_addr = 'ipc://127.0.0.1:9999'
    pub_addr = 'ipc://127.0.0.1:9998'

    # Make sure mongrel2's config is in sync with this.
    config = {
        'handler_tuples': ((r'^/brubeck', DemoHandler),),
        'template_loader': load_jinja2_env('./templates/jinja2'),
    }

    app = Brubeck((pull_addr, pub_addr), **config)
    app.run()
