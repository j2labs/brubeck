#!/usr/bin/env python


from brubeck.request_handling import Brubeck
from brubeck.models import User
from brubeck.templating import Jinja2Rendering, load_jinja2_env
from brubeck.connections import WSGIConnection, Mongrel2Connection
import sys
import logging
import Image
import StringIO


###
### Handlers
###

class UploadHandler(Jinja2Rendering):
    def get(self):
        """Offers login form to user
        """
        return self.render_template('landing.html')
    
    def post(self):
        """Checks credentials with decorator and sends user authenticated
        users to the landing page.
        """
        if hasattr(self.message, 'files'):
            print 'FILES:', self.message.files['data'][0]['body']
            im = Image.open(StringIO.StringIO(self.message.files['data'][0]['body']))
            print 'IM:', im
            im.save('word.png')
        return self.redirect('/')


###
### Configuration
###
    
config = {
    #'msg_conn': WSGIConnection(),
    'msg_conn': Mongrel2Connection("tcp://127.0.0.1:9999", "tcp://127.0.0.1:9998"),
    'handler_tuples': [(r'^/', UploadHandler)],
    'template_loader': load_jinja2_env('./templates/multipart'),
}

app = Brubeck(**config)
app.run()
