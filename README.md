# What Is Brubeck?

__Brubeck__ is a flexible Python web framework that aims to make the process of building scalable web services easy.

The Brubeck model resembles what companies build when they operate at large scale, but working with it will feel like what you're used to from other frameworks.

* No confusing callbacks
* No database opinions
* Built-in distributed load balancing


## Example: Hello World

This is a whole Brubeck application. 

    class DemoHandler(WebMessageHandler):
        def get(self):
            self.set_body('Hello world')
            return self.render()

    urls = [(r'^/', DemoHandler)]
    mongrel2_pair = ('ipc://127.0.0.1:9999', 'ipc://127.0.0.1:9998')

    app = Brubeck(mongrel2_pair=mongrel2_pair,
                  handler_tuples=urls)
    app.run()


## Features

Brubeck gets by with a little help from it's friends:

* [Mongrel2](http://mongrel2.org): lean & fast, asynchronous web serving
* [Eventlet](http://eventlet.net): non-blocking I/O & coroutines
* [ZeroMQ](http://zeromq.org): fast messaging & supports most languages
* [DictShield](https://github.com/j2labs/dictshield): data modeling & validation with no database opinions

Please also see this completely unscientific comparison of Brubeck and Tornado:

* [500 concurrent connections for 10 seconds](https://gist.github.com/882555)


## Complete Example: Listsurf

__Listsurf__ is a simple to way to save links. Yeah... another delicious clone!

It serves as a basic demonstration of what a complete site looks like when you build with Brubeck. It has authentication with secure cookies, offers a JSON API, uses [Jinja2](http://jinja.pocoo.org/) for templating and stores data in [MongoDB](http://mongodb.org).

* [Listsurf on GitHub](https://github.com/j2labs/listsurf)


# Closer Look At The Code

In this section we'll discuss writing a request handler, adding user authentication and rendering pages with templates.


## Handling Requests

The framework can be used for different requirements. It can be lean and lightweight for high throughput or you can fatten it up and use it for rendering pages in a database backed CMS.

The general architecture of the system is to map requests for a specific URL to some [callable](http://docs.python.org/library/functions.html#callable) for processing the request. The configuration attempts to match handlers to URL's by inspecting a list of `(url pattern, callable)` tuples.

Some people like to use classes as handlers. Some folks prefer to use functions. Brubeck supports both.


### MessageHandler Classes

When a class model is used, the class will be instantiated for the life of the request and then thrown away. This makes building state for each request fairly easy.

Brubeck's `MessageHandler` design is similar to what you see in [Tornado](https://github.com/facebook/tornado), or [web.py](http://webpy.org/). 

To answer HTTP GET requests, implement `get()` on a WebMessageHandler instance.

    class DemoHandler(WebMessageHandler):
        def get(self):
            self.set_body('Take five!')
            return self.render()

Then we add `DemoHandler` to the routing config and instantiate a Brubeck instance. 

    urls = [(r'^/brubeck', DemoHandler)]
    config = {
        'handler_tuples': urls,
        ...
    }
    
    Brubeck(**config).run()

* [Runnable demo](https://github.com/j2labs/brubeck/blob/master/demos/demo_minimal.py)


### Functions and Decorators

If you'd prefer to just use a simple function, you instantiate a Brubeck instance and wrap your function with the `add_route` decorator. 

That looks like this:

    app = Brubeck(mongrel2_pair=('ipc://127.0.0.1:9999', 
                                 'ipc://127.0.0.1:9998'))

    @app.add_route('^/brubeck', method='GET')
    def foo(application, message):
        return http_response('Take five!', 200, 'OK', {})

    app.run()

* [Runnable demo](https://github.com/j2labs/brubeck/blob/master/demos/demo_noclasses.py)


## Templates

Brubeck currently supports [Jinja2](http://jinja.pocoo.org/) or [Tornado](http://www.tornadoweb.org/documentation#templates) templates.

Template support is contained in `brubeck.templates` as rendering mixins. Each Mixin will attach a `render_template` function to your handler and overwrite the default `render_error` to produce templated errors messages.

Using a template system is then as easy as calling `render_template` with the template filename and some context, just like you're used to.


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
        ...

* [Runnable demo](https://github.com/j2labs/brubeck/blob/master/demos/demo_tornado.py)
* [Demo templates](https://github.com/j2labs/brubeck/tree/master/demos/templates/tornado)


### Template Loading

Along with the template rendering, you must provide the path to your templates. If Jinja2 templates serve your needs, Providing that path in a call to `load_jinja2_env` is all you need.

That looks like this:

    from brubeck.templating import load_jinja2_env

    config = {
        template_loader=load_jinja2_env('./templates/jinja2')
        ...
    }


### Custom Rendering

If you have something else in mind, you'll be glad to know `template_loader` can be any callable that loads a rendering environment. Brubeck calls this during initialization and attach the output to `self.template_env`, which you use in your handlers.


## Auth

Authentication can be provided by decorating functions with the `@web_authenticated` decorator. This decorator expects the handler to have a `current_user` property that returns either an authenticated `User` model or None. 

The `UserHandlingMixin` provides functionality for authenticating a user and creating the `current_user` property. 

The work that's required will depend on how you build your system. The authentication framework uses a DictShield Document to create the `User` model, so you can implement a database query or check user information in a sorted CSV. Either way, you still get the authentication framework you need.

In practice, this is what your code looks like.

    from brubeck.auth import web_authenticated, UserHandlingMixin

    class DemoHandler(WebMessageHandler, UserHandlingMixin):
        @web_authenticated
        def post(self):
            ...

The `User` model in brubeck.auth will probably serve as a good basis for your needs. A Brubeck user looks roughly like below.

    class User(Document):
        """Bare minimum to have the concept of a User.
        """
        username = StringField(max_length=30, required=True)
        email = EmailField(max_length=100)
        password = StringField(max_length=128)
        is_active = BooleanField(default=False)
        last_login = LongField(default=curtime)
        date_joined = LongField(default=curtime)        
        ...

* [Runnable demo](https://github.com/j2labs/brubeck/blob/master/demos/demo_auth.py)


### Secure Cookies

If you need a session to persist, you can use Brubeck's secure cookies to track users.

You first add the cookie secret to your Brubeck config.

    config = {
        'cookie_secret': 'OMGSOOOOSECRET',
        ...
    }

Then retrieve the cookie value by passing the application's secret key into the `get_cookie` function.

    # Try loading credentials from secure cookie
    user_id = self.get_cookie('user_id',
                              secret=self.application.cookie_secret)

What you do from there is up to you.


# Brubeck.io
