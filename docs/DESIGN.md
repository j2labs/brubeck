# Bird's Eye View

Brubeck processes and responds to messages sent from Mongrel2. By splitting the processing into a pipeline of lightweight [coroutines](http://en.wikipedia.org/wiki/Coroutine), Brubeck can handle a large number of tasks simultaneously. Many more tasks than tradition OS threads allow.


## Goals

* __Be Fast__: Brubeck is currently very fast. We intend to keep it that way.

* __Scalable__: Massive scaling capabilities should be available out of the box.

* __Friendly__: Should be easy for Python hackers of any skill level to use.

* __Pluggable__: Brubeck can speak to any language and any database.


## Contributors

Brubeck wouldn't be what it is without help from:

[James Dennis](https://github.com/j2labs), [Andrew Gwozdziewycz](https://github.com/apgwoz), [Malcolm Matalka](https://github.com/orbitz/), [Dion Paragas](https://github.com/d1on/), [Duane Griffin](https://github.com/duaneg), [Faruk Akgul](https://github.com/faruken), [Seth Murphy](https://github.com/sethmurphy), [John Krauss](https://github.com/talos), [Ben Beecher](https://github.com/gone), [Jordan Orelli](https://github.com/jordanorelli), [Michael Larsen](https://github.com/mghlarsen), [Moritz](https://github.com/m2w), [Dmitrijs Milajevs](https://github.com/dimazest), [Paul Winkler](https://github.com/slinkp), [Chris McCulloh](https://github.com/st0w), [Nico Mandery](https://github.com/nmandery), [Victor Trac](https://github.com/victortrac)


# The General Design

Brubeck's primary purpose is to pull requests from some interface and work on them. It accomplishes this by either listening on a ZeroMQ socket or by acting as a WSGI callback. It receives a message, routes it to a handler function for processing, and then sends the reply. 


## Requests & Request Handling

In `brubeck.request_handling` we see a section for message pipelining coroutines, a section for message handling and a section for the Brubeck application logic. A Brubeck instance creates a Mongrel2 connection and provides a `run()` function to start waiting for Mongrel2 messages. `run()` is similar to `IOLoop.start()` in Tornado.


### Configuring

To set up a Brubeck instance, you configure two ZeroMQ sockets, map a handler to a URL, and call `run()`. That looks like this:

    config = {
        'msg_conn: Mongrel2Connection('ipc://127.0.0.1:9999', 
                                      'ipc://127.0.0.1:9998')
        'handler_tuples': [(r'^/url/path', SomeHandler)]
    }
    
    Brubeck(**config).run()


### Routing Coroutines

The general strucuture for the preprocessing, message processing and post-processing coroutines is defined in here too. 

* `route_message` is the first function called when a Mongrel2 message arrives. It looks at the message and asks the application for a callable that can process the message. It then spawns a follow-up coroutine which is responsible for actually processing the message.

* `request_handler` is the follow-up coroutine. It's job is simply to call the handler and spawn the final coroutine for post-processing.

* `result_handler` is the final coroutine. It currently just takes the handler's response and sent it along to Mongrel2.


### Message Routing and Handling

Message routing is little more than a regex match from the URL to a callable for handling the URL. Even though only a callable is needed, I generally use Tornado style classes for handling messages.

I extend the capabilities of message handlers by adding Mixin's in. Authentication, template rendering and argument handling are done this way to keep code in one place when possible. State for the message handling is attached to the callable as necessary and the callable is thrown away when the second pipelining coroutine completes. 

In the MessageHandler class we `__call__` defined. This function let's the MessageHandler class provide the details for routing the message to the appropriate method handler. As previously mentioned, this means an HTTP GET request will route to MessageHandler.get() or it will call MessageHandler.unsupported() for a response.

The response just needs to be a string. MessageHandler is a base class for handling ZeroMQ messages. The WebMessageHandler will provide a fully qualified HTTP response for Mongrel2. This is a subtle detail about Brubeck: it is an asynchronous ZeroMQ message handler masquerading as a Mongrel2 handler.

By using a callable and expecting a string response, leaner programmers can avoid using classes altogether. Map a URL to a function directly.


## mongrel2.py

This module provides functions and a class for parsing a message from Mongrel2 and a class for managing the details of a Mongrel2 connection.

A call to `recv()` on connection instance will block until a message arrives or the Eventlet scheduler works on something else. A `Request` instance is returned by `recv()` and provides a few functions for inspecting the payload sent by Mongrel2.

`Request.method()` will tell us whether the message was HTTP GET or POST, etc. `Request.version()` tells us the HTTP version used.

This class is kept simple on purpose and could be used outside Brubeck for parsing Mongrel2 messages.
