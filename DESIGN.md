# The General Design

Brubeck reads and processes ZeroMQ messages, as sent by Mongrel2, by splitting the processing into a pipeline of [coroutines](http://en.wikipedia.org/wiki/Coroutine). Cooperative threading makes threading a little bit easier to think about but the big gain is the lightweight process model, as provided by [Greenlet](http://pypi.python.org/pypi/greenlet).

Brubeck uses [non-blocking I/O](http://en.wikipedia.org/wiki/Asynchronous_I/O), as provided by [eventlet](http://eventlet.net/). By using Eventlet, Brubeck might be able to turn your blocking code into [non-blocking code](http://eventlet.net/doc/patching.html) automatically.

Brubeck offers a database-agnostic data modeling layer by using [DictShield](https://github.com/j2labs/dictshield). DictShield provides ways of structuring and validating data without taking a stance on which database system you use.

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
