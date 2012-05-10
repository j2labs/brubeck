# AutoAPI

Brubeck combines the metaprogramming in DictShield along with the assumption
that REST is generally similar to CRUD to provide a mechanism for generating
APIs from DictShield models.

There are two things that must be consider: 

1. Data Processing
2. Persistence


## Data Processing

The data processing is essentially to provide GET, POST, PUT and DELETE for a
document design. The document provides a mechanism for validating the ID of a
document, which is useful for both GET and DELETE. It also provides the
mechanism for validating an entire document, as we'd expect to receive with
either POST or PUT.

We could define a simple model to look like this:

    class Todo(Document):
        completed = BooleanField(default=False)
        text = StringField(required=True)
        class Meta:
            id_options = {'auto_fill': True}

DictShield provides a way to validate input against this structure. It also
provides a way to format output, like when we serialize the structure to JSON,
with some fields removed, based on what permissions are available to the user.

We'll create a `Todo` instance.

    >>> t = Todo(text='This is some text')
    >>> t.validate()
    True
    
Let's serialize it to a Python dictionary. This is probably what we'd save in
a database.

    >>> t.to_python()
    {'_types': ['Todo'], 'text': u'This is some text', 'completed': False, '_id': UUID('c4ac6aff-737c-47db-ab07-fbe402b08d1c'), '_cls': 'Todo'}

Or maybe we're just gonna store JSON in something.

     >>> t.to_json()
     '{"_types": ["Todo"], "text": "This is some text", "completed": false, "_id": "7e48a600-f599-4a3a-9244-73760841f70e", "_cls": "Todo"}'
     
It's useful for APIs too, because you can combine one of it's `make_safe`
functions with whatever access rights the user has. DictShield provides the 
concept of *owner* and *public* in the form of a blacklist and a whitelist
respectively.

    >>> Todo.make_json_ownersafe(t)
    '{"text": "This is some text", "completed": false}'
    >>> 

If we provide GET and PUT we will need to handle ID fields. DictShield
documents let us validate individual fields if we want. That looks like this:

    >>> Todo.id.validate('c4ac6aff-737c-47db-ab07-fbe402b08d1c')
    UUID('c4ac6aff-737c-47db-ab07-fbe402b08d1c')
    
We can see that the returned value is the input coerced into the type of the
field. 

This is what failed validation looks like, notice that the input is a munged
version of the input above.

    >>> Todo.id.validate('c4ac6aff-737c-47db-ab07-fbe402b0c')
    Traceback (most recent call last):
      File "<stdin>", line 1, in <module>
      File "/Users/jd/Projects/dictshield/dictshield/fields/base.py", line 178, in validate
        self.field_name, value)
    dictshield.base.ShieldException: Not a valid UUID value - None:c4ac6aff-737c-47db-ab07-fbe402b0c
    

## Persistence

Persistence is then handled by way of a `QuerySet`. A dict based QuerySet,
called `DictQueryset`, is provided by default. Other implementations for
supporting MongoDB, Redis and MySQL are on the way.

The interface to the QuerySets is defined in the `AbstractQueryset`. We see
some familiar names defined: `create()`, `read()`, `update()` and `destroy()`.
These functions then either call `create_one` or `create_many` for each CRUD
operation.

CRUD doesn't map exactly to REST, but it's close, so Brubeck attempts to
accurately cover REST's behavior using CRUD operations. It's not a 1:1 mapping.

The `DictQueryset` then subclasses `AbstractQueryset` and implements
`create_one`, `create_many`, etc. These functions are focused primarily around
a document's ID. The ID, as provided by DictShield, is how we identify which
documents should be deleted or updated or retrieved.


## Putting Both Together

Putting the two together is a simple process.

First we import the persistence layer and define the data's structure:

    from brubeck.queryset import DictQueryset

    class Todo(Document):
        completed = BooleanField(default=False)
        text = StringField(required=True)
        class Meta:
            id_options = {'auto_fill': True}
            
Then we subclass `AutoAPIBase` and define two fields, `queries` and `model`.
The model is our Document from above. The queries is whichever queryset we're
using.

    class TodosAPI(AutoAPIBase):
        queries = DictQueryset()
        model = Todo

Setup a Brubeck instance as you normally would, but then register the AutoApi
instance with the app.

    app = Brubeck(...)
    app.register_api(TodosAPI)

Done.


# Examples

Brubeck comes with an AutoAPI example that is slightly more elaborate than what
we see above.

* [AutoAPI Demo](https://github.com/j2labs/brubeck/blob/master/demos/demo_autoapi.py)

There is also an example where Brubeck's AutoAPI is used in conjunction with
the well known Todo list javascript demo.

* [Todos](https://github.com/j2labs/todos)
