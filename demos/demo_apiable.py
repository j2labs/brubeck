#!/usr/bin/env python


from brubeck.request_handling import Brubeck, AutoAPIBase, WebMessageHandler
from brubeck.queryset import DictQueryset
from brubeck.templating import Jinja2Rendering, load_jinja2_env


from dictshield.document import Document
from dictshield.fields import (StringField,
                               BooleanField)


class Todo(Document):
    """Bare minimum for a todo
    """
    # status fields
    completed = BooleanField(default=False)
    deleted = BooleanField(default=False)
    archived = BooleanField(default=False)
    
    title = StringField(required=True)

    def __unicode__(self):
        return u'%s' % (self.title)


class TodosAPI(AutoAPIBase):
    queries = DictQueryset(db_conn={})
    model = Todo

class BaseHandler(Jinja2Rendering):
    pass

class TodosHandler(BaseHandler):
    def get(self):
        """A list display matching the parameters of a user's dashboard. The
        parameters essentially map to the variation in how `load_listitems` is
        called.
        """
        return self.render_template('todos.html')


###
### Configuration
###

# Routing config
handler_tuples = [
    (r'^/$', TodosHandler),
]

# Application config
config = {
    'mongrel2_pair': ('ipc://127.0.0.1:9999', 'ipc://127.0.0.1:9998'),
    'handler_tuples': handler_tuples,
    'template_loader': load_jinja2_env('./templates/apiable'),
}

# Instantiate app instance
app = Brubeck(**config)
app.register_api(TodosAPI)
app.run()

