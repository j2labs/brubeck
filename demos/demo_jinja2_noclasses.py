#! /usr/bin/env python


from brubeck.request_handling import Brubeck, render
from brubeck.connections import Mongrel2Connection
from brubeck.templating import  load_jinja2_env, Jinja2Rendering


app = Brubeck(msg_conn=Mongrel2Connection('tcp://127.0.0.1:9999',
                                          'tcp://127.0.0.1:9998'),
              template_loader=load_jinja2_env('./templates/jinja2'))


@app.add_route('^/', method=['GET', 'POST'])
def index(application, message):
    name = message.get_argument('name', 'dude')
    context = {
        'name': name,
    }
    body = application.render_template('success.html', **context)
    return render(body, 200, 'OK', {})


app.run()
