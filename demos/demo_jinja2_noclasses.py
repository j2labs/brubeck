#! /usr/bin/env python

from brubeck.request_handling import Brubeck, http_response
from brubeck.templating import  load_jinja2_env
from brubeck.templating import Jinja2Rendering

app = Brubeck(mongrel2_pair=('ipc://127.0.0.1:9999',
                             'ipc://127.0.0.1:9998'),
              template_loader=load_jinja2_env('./templates/jinja2'))

@app.add_route('^/', method=['GET', 'POST'])
def index(application, message):
    ### Check the name argument on the message
    name = message.get_argument('name', 'dude')
    context = {
        'name': name,
    }

    ### Template handling could be cleaner here
    jinja_env = application.template_env
    template = jinja_env.get_template('success.html')
    body = template.render(**context)

    ### Return HTTP response
    return http_response(body, 200, 'OK', {})

app.run()
