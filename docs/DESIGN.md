# Bird's Eye View

Brubeck processes and responds to messages sent from Mongrel2. By splitting the processing into a pipeline of lightweight [coroutines](http://en.wikipedia.org/wiki/Coroutine), Brubeck can handle a large number of tasks simultaneously. Many more tasks than tradition OS threads allow.

## Goals

* __Be Fast__: Brubeck is currently very fast. We intend to keep it that way.

* __Scalable__: Massive scaling capabilities should be available out of the box.

* __Friendly__: Should be easy for Python hackers of any skill level to use.

* __Pluggable__: Brubeck can speak to any language and any database.

## Contributors

Brubeck wouldn't be what it is without help from:

* [James Dennis](https://github.com/j2labs)
* [Andrew Gwozdziewycz](https://github.com/apgwoz)
* [Malcolm Matalka](https://github.com/orbitz/)
* [Dion Paragas](https://github.com/d1on/)
* [Duane Griffin](https://github.com/duaneg)
* [Faruk Akgul](https://github.com/faruken)

## Reading This Document

Veteran Python hackers can probably skip past the dependencies section.

Please keep reading if you're unfamiliar with ZeroMQ, Eventlet, Mongrel2 or DictShield for a brief introduction to each.


# Dependencies

Brubeck leverages a few awesome Python packages for most of it's magic. Credit must be given where credit is due. 


## Mongrel2 + ZeroMQ

Mongrel2 is an asynchronous and language-agnostic (!!) web server by [Zed Shaw](http://zedshaw.com/). Mongrel2 handles everything relevant to HTTP and has facilities for passing request handling to external services via ZeroMQ sockets. 

This decoupling of the webserver from the request handling allows for interesting web service topologies. It also allows for easy scaling, since you can simply connect a new handler to existing Mongrel2 instances and immediately become part of the handler pool.

Similarly, if a handler dies, it is removed from the pool immediately. Contrast this with nginx likely waiting 10 seconds before it notices the upstream host is down.

* [Mongrel2](http://mongrel2.org)
* [ZeroMQ guide](http://zguide.zeromq.org/)


## Eventlet

Eventlet is a concurrent networking library for Python. We get concurrency in the form of [coroutines](http://pypi.python.org/pypi/greenlet) and an implicit scheduler. The coroutines, which can be thought of as something of a replacement for threads, are very cheap. So cheap that you don't have to think too hard on how many you spawn. 


### Coroutines

Brubeck is basically a pipeline of coroutines attempting to fulfill web requests. By using coroutines in conjunction with a scheduler, Eventlet has the necessary pieces to also provide nonblocking I/O.

Python programmers have seen asynchronous, nonblocking I/O typically done as a chain of callbacks that interact with a scheduler. System design can become foggy when many callbacks are chained together. And, many drivers for things like databases are synchronous / blocking too, so steps must be taken to make them compatible.


### Back To Eventlet

Eventlet makes this easier through implicit context switching. Each time your code reaches a I/O point, eventlet will step in and switch to some other coroutines and handle the complication for you, implicitly.

Brubeck then shares time between reading Mongrel2 messages, processing the messages, and writing responses back to Mongrel2. Your request handler is inserted inbetween those steps, making all of your I/O calls part of the asynchronous, nonblocking system automatically.

The end result is that your code looks synchronous (read: no callback spaghetti)

* [Eventlet](http://eventlet.net).


### Alternatives

Some folks prefer [gevent](http://gevent.org) over eventlet. Brubeck has a branch adding support for that. (Thanks [d1on](https://github.com/d1on))

* [gevent support](https://github.com/j2labs/brubeck/tree/gevent)

There are also reasonable arguments for explicit context switching. If prefer that model, I recommend the systems below:

* [Twisted Project](http://twistedmatrix.com/)
* [Node.js](http://nodejs.org)
* [Web Machine](https://bitbucket.org/justin/webmachine/wiki/Home)


## DictShield

DictShield offers input validation and structuring without taking a stance on what database you should be using. There are many good reasons to use all kinds of databases. DictShield only cares about Python dictionaries. If you can get your data into those, DictShield will handle the rest. 

DictShield strives to be database agnostic in the same way that Mongrel2 is language agnostic.

* [DictShield](https://github.com/j2labs/dictshield)


# The General Design

Now that we know what the dependencies offer, let's consider how to put them together. 

The general idea is to pull a message off the ZeroMQ socket, route it to the correct function for handling it and then send a response back to Mongrel2. This process takes place across three coroutines. If you are implementing a message handler, your code would run in the second coroutine. The other two are hidden away inside Brubeck for pre and post-processing.

To set up a Brubeck instance, you configure two ZeroMQ sockets, some routes for handling URL's, and call `run()`.

    config = {
        'mongrel2_pair': ('ipc://127.0.0.1:9999', 'ipc://127.0.0.1:9998')
        'handler_tuples': [(r'^/url/path', SomeHandler)]
    }
    
    Brubeck(**config).run()


## request_handling.py

In `brubeck.request_handling` we see a section for message pipelining coroutines, a section for message handling and a section for the Brubeck application logic. A Brubeck instance creates a Mongrel2 connection and provides a `run()` function to start waiting for Mongrel2 messages. `run()` is similar to `IOLoop.start()` in Tornado.


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
