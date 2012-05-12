#!/usr/bin/env python

"""To use this demo, try entering the following commands in a terminal:

    curl http://localhost:6767/todo/ | python -mjson.tool
    
    curl -H "content-type: application/json" -f -X POST -d '{"id": "111b4bb7-55f5-441b-ba25-c7a4fd99442c", "text": "Watch more bsg", "order": 1}' http://localhost:6767/todo/111b4bb7-55f5-441b-ba25-c7a4fd99442c/ | python -m json.tool
    
    curl -H "content-type: application/json" -f -X POST -d '{"id": "222b4bb7-55f5-441b-ba25-c7a4fd994421", "text": "Watch Blade Runner", "order": 2}' http://localhost:6767/todo/222b4bb7-55f5-441b-ba25-c7a4fd994421/ | python -m json.tool
    
    curl http://localhost:6767/todo/ | python -mjson.tool
    
    curl http://localhost:6767/todo/222b4bb7-55f5-441b-ba25-c7a4fd994421/ | python -mjson.tool
    
    curl -H "content-type: application/json" -f -X DELETE http://localhost:6767/todo/222b4bb7-55f5-441b-ba25-c7a4fd994421/ 
    
    curl http://localhost:6767/todo/ | python -mjson.tool
    
    curl -H "content-type: application/json" -f -X POST -d '[{"id": "333b4bb7-55f5-441b-ba25-c7a4fd99442c", "text": "Write more Brubeck code", "order": 3},{"id": "444b4bb7-55f5-441b-ba25-c7a4fd994421", "text": "Drink coffee", "order": 4}]' http://localhost:6767/todo/ | python -m json.tool
    
    curl http://localhost:6767/todo/ | python -mjson.tool
    
    curl -H "content-type: application/json" -f -X POST -d '{"id": "b4bb7-55f5-441b-ba25-c7a4fd994421", "text": "Watch Blade Runner", "order": 2}' http://localhost:6767/todo/222b4bb7-55f5-441b-ba25-c7a4fd994421/ | python -m json.tool
    
    curl -H "content-type: application/json" -f -X POST -d '{"id": "b4bb7-55f5-441b-ba25-c7a4fd994421", "text": "Watch Blade Runner", "order": 2}' http://localhost:6767/todo/b4bb7-55f5-441b-ba25-c7a4fd994421/ | python -m json.tool
"""

from brubeck.request_handling import Brubeck
from brubeck.autoapi import AutoAPIBase
from brubeck.queryset import DictQueryset
from brubeck.templating import Jinja2Rendering, load_jinja2_env
from brubeck.connections import Mongrel2Connection

from dictshield.document import Document
from dictshield.fields import (StringField,
                               BooleanField)


### Todo Model
class Todo(Document):
    """Bare minimum for a todo
    """
    # status fields
    completed = BooleanField(default=False)
    deleted = BooleanField(default=False)
    archived = BooleanField(default=False)
    title = StringField(required=True)
    class Meta:
        id_options = {'auto_fill': True}


### Todo API
class TodosAPI(AutoAPIBase):
    queries = DictQueryset()
    model = Todo
    def render(self, **kwargs):
        return super(TodosAPI, self).render(hide_status=True, **kwargs)


### Flat page handler
class TodosHandler(Jinja2Rendering):
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
    'msg_conn': Mongrel2Connection('tcp://127.0.0.1:9999', 'tcp://127.0.0.1:9998'),
    'handler_tuples': handler_tuples,
    'template_loader': load_jinja2_env('./templates/autoapi'),
}

# Instantiate app instance
app = Brubeck(**config)
app.register_api(TodosAPI)
app.run()

