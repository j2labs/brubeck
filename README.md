# Brubeck

Brubeck is an asynchronous, non-blocking web framework written in Python. It can also be used as an asynchronous, non-blocking message processing framework to handle the longer running jobs. In both cases, it aims to be minimal and efficient.

The code is available here: [https://github.com/j2labs/brubeck](https://github.com/j2labs/brubeck).

Brubeck is a system for building cloud-like API's quickly. By using Eventlet, ZeroMQ and Mongrel2 for it's concurrency, messaging and web serving Brubeck users focus exclusively on writing request handling code.


## Goals

* Be flexible and be scalable. The most important goal is to provide a flexible, scalable web system.

* The second goal is to be agnostic of as many moving parts as possible. Mongrel2 gains language agnosticism by using ZeroMQ for socket-based communication. Brubeck does the same. Brubeck, however, takes this a step further by providing a data modeling layer that is database agnostic too.

* The third goal is to provide tools that make building cloud-like API's easy. A common theme is to have a stream that can be explored via timestamps on data. That stream probably needs authentication at times. It probably needs paging too. Most API's offer something along these lines, so Brubeck will too.


## Further reading

Brubeck has:

* [An Install Guide](https://github.com/j2labs/brubeck/blob/master/docs/INSTALLING.md)
* [A Design Document](https://github.com/j2labs/brubeck/blob/master/docs/DESIGN.md)
* [A BSD License](https://github.com/j2labs/brubeck/blob/master/docs/LICENSE.md)
* [A Requirements File](https://github.com/j2labs/brubeck/blob/master/requirements.txt)


## Complete example: Listsurf

Take a look at [listsurf](https://github.com/j2labs/listsurf). Listsurf is a
to way to save links. Yeah, another delicious clone! Well, sorta. But it's also
the building block towards projects for *most* people and can teach new Brubeck
users how to build a website and JSON API with data stored in MongoDB.

* [listsurf](https://github.com/j2labs/listsurf)

# Quick Look At The Code

There are different opinions on how to properly set up routing systems in Python. 

One group likes to have classes that implement particular functions. Often enough, this looks like a `MessageHandler` implementing `get()` to respond to HTTP GET requests.

Another group likes to have just have funcitons and then apply some decorators for routing. This is similar to what you see in Flask or Bottle. 

Brubeck supports both.


## MessageHandler Classes

Brubeck's `MessageHandler` design is similar to what you see in [Facebook's Tornado](https://github.com/facebook/tornado). 

To answer HTTP GET requests, implement `get()` on a WebMessageHandler instance. We'll map the class to the URL in a second.

    class DemoHandler(WebMessageHandler):
        def get(self):
            self.set_body('Take five!')
            return self.render()

The handler classes are mapped to URL patterns by passing a list of tuples to Brubeck when you run the app. The list might looks like this.

    config = {
        'handler_tuples': [(r'^/brubeck', DemoHandler)],
        'mongrel2_pair': ('ipc://127.0.0.1:9999', 'ipc://127.0.0.1:9998'),
    }
    Brubeck(**config).run()

* [Runnable demo](https://github.com/j2labs/brubeck/blob/master/demos/demo_minimal.py)


## Functions and Decorators

Brubeck supports wrapping funcitons with route information if that's the style you like. 

First, you instantiate a Brubeck instance with a pair of Mongrel2 sockets.

    app = Brubeck(mongrel2_pair=('ipc://127.0.0.1:9999', 
                                 'ipc://127.0.0.1:9998'))

Then you wrap some functions with the `add_route` decorator.

    @app.add_route('^/brubeck', method='GET')
    def foo(application, message):
        return http_response('Take five!', 200, 'OK', {})

Start the app and you're done.

    app.run()

This is the simplest model to get start answering URL's with Python functions.

* [Runnable demo](https://github.com/j2labs/brubeck/blob/master/demos/demo_noclasses.py)


# Routing URL's

As we saw above, handling URL's is as easy as mapping a URL to a class.

    handler_tuples = [(r'^/brubeck', DemoHandler)]

Or as easy as decorating a funciton.

    @app.add_route('^/brubeck', method='GET')
    def foo(application, message):
        ...

In both cases, we match a regex `^/brubeck` against the requested URL. If we find a match, we send the request to the handler.

A class structure let's me easily attach state to the request while providing functions or Mixins for processing the request. One mixin might add a ._attribute1 and a follow up function can check if that value exists. 

State *could* be maintained otherwise too. If that's your cup of tea, the decorator approach is likely for you.

Auth and templates are good examples of how to extend your `MessageHandler` instances.


## Auth

Authentication can be provided by decorating functions, similar to Tornado. The `@web_authenticated` decorator expects the handler to have a `current_user` property that returns either an authenticated `User` model or None. The `UserHandlingMixin` provides the functionality for authenticating a user and creating that `current_user` property. 

By using the decorator, you trigger a call provided by the mixin. Nice and simple!

The work that's required will depend on how you build your system. The authentication framework uses a DictShield Document to create the `User` model, so you can implement the database query however you see fit. You still get the authentication framework you need.

In practice, this is what your code looks like.

    from brubeck.auth import web_authenticated, UserHandlingMixin

    class DemoHandler(WebMessageHandler, UserHandlingMixin):
        @web_authenticated
        def post(self):
            ...

The `User` model in brubeck.auth will probably serve as a good basis for your needs. A Brubeck user looks like below.

    class User(Document):
        """Bare minimum to have the concept of a User.
        """
        username = StringField(max_length=30, required=True)
        password = StringField(max_length=128)
        ...

* [Runnable demo](https://github.com/j2labs/brubeck/blob/master/demos/demo_auth.py)


## Templates

Templates are supported by implementing a *Rendering Mixin. This Mixin will attach a `render_template` function and overwrite the `render_error` template to produce errors messages via the template engine.

Using a template system is then as easy as calling `render_template` with the template filename and context. `render_template` will call `render` for you.


### Jinja2

Using Jinja2 template looks like this.

    from brubeck.templating import Jinja2Rendering
    
    class DemoHandler(WebMessageHandler, Jinja2Rendering):
        def get(self):
            context = {
                'name': 'J2 D2',
            }
            return self.render_template('success.html', **context)

* [Runnable demo](https://github.com/j2labs/brubeck/blob/master/demos/demo_jinja2.py)
* [Demo templates](https://github.com/j2labs/brubeck/tree/master/demos/templates/jinja2)


### Tornado

Tornado templates are supported by the TornadoRendering mixin. The code looks virtually the same to keep mixing template systems lightweight.

    from brubeck.templating import TornadoRendering
    
    class DemoHandler(WebMessageHandler, TornadoRendering):
        def get(self):
            context = {
                'name': 'J2 D2',
            }
            return self.render_template('success.html', **context)

* [Runnable demo](https://github.com/j2labs/brubeck/blob/master/demos/demo_tornado.py)
* [Demo templates](https://github.com/j2labs/brubeck/tree/master/demos/templates/tornado)


# J2 Labs LLC

Brubeck is a J2 Labs creation. I hope you find it useful.
