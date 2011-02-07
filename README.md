# Brubeck

Brubeck is a [Mongrel2](http://mongrel2.org/) framework. It is designed to read and process ZeroMQ messages, as sent by Mongrel2, by splitting the processing into a pipeline of [coroutines](http://en.wikipedia.org/wiki/Coroutine). 

Brubeck uses [non-blocking I/O](http://en.wikipedia.org/wiki/Asynchronous_I/O), as provided by [eventlet](http://eventlet.net/). It can even turn existing blocking code into [non-blocking code](http://eventlet.net/doc/patching.html).

Mongrel2 is an asynchronous and language-agnostic (!!) web server by [Zed Shaw](http://zedshaw.com/). Mongrel2 handles everything relevant to HTTP and has facilities for passing request handling to external services via ZeroMQ sockets. By nature of using ZeroMQ, Mongrel2 becomes asynchronous and handles messages as they come in.

The Mongrel2 handling code is based on Zed's python in mongrel2's source.

## Code

The code is on github: [https://github.com/j2labs/brubeck](https://github.com/j2labs/mongrevent).

It is also [BSD licensed](http://en.wikipedia.org/wiki/BSD_licenses).

# The Design

Still coming together as I figure out how to do this.

For now, the documentation for [MongrEvent] is close to sufficient. Also check out the code in `demo.py` for an example of how to respond to a message for an HTTP request.
