# Message Handlers

Let's take a look at that demo handler from before.

    class DemoHandler(WebMessageHandler):
        def get(self):
            self.set_body('Take five')
            return self.render()
    
    options = {
        'handler_tuples': [(r'^/', DemoHandler)],
        'msg_conn': WSGIConnection(port=6767),
    }

    app = Brubeck(**options)
    app.run()

The `DemoHandler` class has a `get()` implementation, so we know that handler answers HTTP GET and that handler is mapped to the root URL, '/'. 

Brubeck is also configured to run as a WSGI server on port 6767. Turn the app on and it will answer requests at http://localhost:6767.


## Handling Requests

The framework can be used for different requirements. It can be lean and lightweight for high throughput or you can fatten it up and use it for rendering pages in a database backed CMS.

The general architecture of the system is to map requests for a specific URL to some [callable](http://docs.python.org/library/functions.html#callable) for processing the request. The configuration attempts to match handlers to URL's by inspecting a list of `(url pattern, callable)` tuples. First regex to match provides the callable.

Some people like to use classes as handlers. Some folks prefer to use functions. Brubeck supports both.

The HTTP methods allowed are: GET, POST, PUT, DELETE, HEAD, OPTIONS, TRACE, CONNECT. 


### MessageHandler Classes

When a class model is used, the class will be instantiated for the life of the request and then thrown away. This keeps our memory requirements nice and light.

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
    
Notice the url regex is `^/brubeck`. This will put our handler code on `http://hostname/brubeck`. (Probably [http://localhost:6767/brubeck](http://localhost:6767/brubeck)).

* [Runnable demo](https://github.com/j2labs/brubeck/blob/master/demos/demo_minimal.py)


### Functions and Decorators

If you'd prefer to just use a simple function, you instantiate a Brubeck instance and wrap your function with the `add_route` decorator. 

Your function will be given two arguments. First, is the `application` itself. This provides the function with a hook almost all the information it might need. The second argument, the `message`, provides all the information available about the request.

That looks like this:

    app = Brubeck(mongrel2_pair=('ipc://127.0.0.1:9999', 
                                 'ipc://127.0.0.1:9998'))

    @app.add_route('^/brubeck', method='GET')
    def foo(application, message):
        return http_response('Take five!', 200, 'OK', {})

    app.run()

* [Runnable demo](https://github.com/j2labs/brubeck/blob/master/demos/demo_noclasses.py)
