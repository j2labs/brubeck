# Brubeck

Brubeck is an asynchronous, non-blocking web framework written in Python. It can also be used as an asynchronous, non-blocking message processing framework to handle the longer running jobs. In both cases, it aims to be minimal and efficient.

The code is available here: [https://github.com/j2labs/brubeck](https://github.com/j2labs/brubeck).

Brubeck is a system for building cloud-like API's quickly. By using Eventlet, ZeroMQ and Mongrel2 for it's concurrency, messaging and web serving Brubeck users focus exclusively on writing request handling code.


## Goals

* Be flexible and be scalable. The most important goal is to provide a flexible, scalable web system.

* The second goal is to be agnostic of as many moving parts as possible. Mongrel2 gains language agnosticism by using ZeroMQ for socket-based communication. Brubeck does the same. Brubeck, however, takes this a step further by providing a data modeling layer that is database agnostic too.

* The third goal is to provide tools that make building cloud-like API's easy. A common theme is to have a stream that can be explored via timestamps on data. That stream probably needs authentication at times. It probably needs paging too. Most API's offer something along these lines, so Brubeck will too.


## Quick glance at the code

Brubeck's design is similar to what you see in [Facebook's Tornado](https://github.com/facebook/tornado). An event loop is provided by [Eventlet's server pattern](http://eventlet.net/doc/design_patterns.html#server-pattern). 

The loop waits on the ZeroMQ socket is uses to connect to Mongrel2. When a message comes in from Mongrel2, Brubeck matches the URL pattern against it's list of handlers. To respond to HTTP GET on a particular URL you map the URL to a handler class and implement `get()`.

    class DemoHandler(WebMessageHandler):
        def get(self):
            self.set_body('Take five!') # hello world is boring
            self.set_status(200)
            return self.render()

The URL map is list of url pattern and handler class pairs. This is how we map `localhost:6767/brubeck` to the `DemoHandler` class.

    handler_tuples = [(r'^/brubeck$', DemoHandler)]

The Mongrel2 communication happens between two sockets. It asks Brubeck to do some work on one socket and hears the response from Brubeck on the other.

    app = Brubeck(('ipc://127.0.0.1:9999', 'ipc://127.0.0.1:9998'), handler_tuples)
    app.run()


# Handler configuration

I like to keep things flexible when possible. I find a class structure for maintaining state in a pipeline of state objects works well. The instance doesn't exist for a long period of time either so state is essentially a snapshot of the relevant environment for processing the request and then that object is tossed away along with the request.

## Auth

Authentication can be provided by decorating functions, similar to Tornado. The `@web_authenticated` decorator expects the handler to have a `current_user` property that returns either an authenticated `User` model or None. The `UserHandlingMixin` provides the functionality for authenticating a user and creating that `current_user` property.

The work that's required will depend on how you build your system. The authentication framework uses a DictShield Document to create the `User` model, so you can implement the database query however you see fit. You still get the authentication framework you need.

In practice, this is what your code looks like.

    from brubeck.auth import web_authenticated, UserHandlingMixin

    class DemoHandler(WebMessageHandler, UserHandlingMixin):
        @web_authenticated
        def post(self):
            ...

## Templates

Templates are supported by implementing a *Rendering Mixin. This Mixin will attach a `render_template` function and overwrite the `render_error` template to produce errors messages via the template engine.

Using a template system is then as easy as calling `render_template` with the template file and context instead of calling `render`.

### Jinja2

Using Jinja2 template looks like this.

    from brubeck.templating import Jinja2Rendering
    
    class DemoHandler(WebMessageHandler, Jinja2Rendering):
        def get(self):
            ...
            context = {
                'name': 'J2 D2',
            }
            return self.render_template('templates/success.html', **context)

### Tornado

Tornado templates are supported by the TornadoRendering mixin. The code looks virtually the same to keep mixing template systems lightweight.

Using Tornado looks exactly the same, except you write `TornadoRendering`.

# Licensing

Brubeck is [BSD licensed](http://en.wikipedia.org/wiki/BSD_licenses).
