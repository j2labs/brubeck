# Bird's eye view

Brubeck reads and processes ZeroMQ messages, as sent by Mongrel2, by splitting the processing into a pipeline of [coroutines](http://en.wikipedia.org/wiki/Coroutine). Cooperative threading makes threading a little bit easier to think about but the big gain is the lightweight process model, as provided by [Greenlet](http://pypi.python.org/pypi/greenlet).

Brubeck uses [non-blocking I/O](http://en.wikipedia.org/wiki/Asynchronous_I/O), as provided by [eventlet](http://eventlet.net/). By using Eventlet, Brubeck might be able to turn your blocking code into [non-blocking code](http://eventlet.net/doc/patching.html) automatically.

Brubeck offers a database-agnostic data modeling layer by using [DictShield](https://github.com/j2labs/dictshield). DictShield provides ways of structuring and validating data without taking a stance on which database system you use.

# Dependencies

Brubeck leverages a few awesome Python packages for most of it's magic. Credit must be given where credit is due.

## Mongrel2 + ZeroMQ

Mongrel2 is an asynchronous and language-agnostic (!!) web server by [Zed Shaw](http://zedshaw.com/). Mongrel2 handles everything relevant to HTTP and has facilities for passing request handling to external services via ZeroMQ sockets. 

Back before Brubeck existed, I covered the gist of how Mongrel2 uses ZeroMQ to fulfill requests in a blog post: [A Short Introduction To Mongrel2](http://j2labs.tumblr.com/post/3201232215/mongrel2-a-short-introduction).

* [Mongrel2](http://mongrel2.org)
* [ZeroMQ guide](http://zguide.zeromq.org/)

## Eventlet

Eventlet is a concurrent networking library for Python. We get concurrency in the form of coroutines and an implicit scheduler. The coroutines, which can be thought of as a replacement for threads, are very cheap. So cheap that you don't have to think too hard on how many you spawn. 

Brubeck, then, is a pipeline of coroutines attempting to fulfill web requests. By using greenlets in conjunction with a scheduler, Eventlet has the necessary pieces to handle nonblocking I/O for us. It can even monkey patch existing Python code, by providing new modules for socket, threading and others. Modules written entirely in Python likely depend on these, so Eventlet transforms them coroutine friendly at a very low level.

* [Evenlet](http://eventlet.net).

## DictShield

DictShield offers input validation and structuring without taking a stance on what database you should be using. There are many good reasons to use all kinds of databases. DictShield only cares about Python structures, so if you can get your data into those, DictShield will handle the rest. 

DictShield strives to be database agnostic in the same way that Mongrel2 is language agnostic.

* [DictShield](https://github.com/j2labs/dictshield)

# The General Design

Now that we know what the dependencies offer, let's consider how to put them together. 

The general idea is to pull a message off the ZeroMQ socket, route it to the correct function for handling it and then send a response back to Mongrel2. As said in the README, the message is done via three coroutines. If you are implementing a message handler, your code would run in the second coroutine.

Setting up a Brubeck instance is then as simple as configuring two ZeroMQ sockets and some routes for handling URL's.

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
