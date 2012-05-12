# Dependencies

Brubeck leverages a few awesome Python packages and some other stuff, mainly in C, for a significant piece of it's capabilities. Credit must be given where credit is due. 


## Web Serving

Brubeck can support Mongrel2 or WSGI. 

### Mongrel2

[Mongrel2](http://mongrel2.org) is an asynchronous and language-agnostic (!!) web server by [Zed Shaw](http://zedshaw.com/). Mongrel2 handles everything relevant to HTTP or Web Sockets and has facilities for passing request handling to external services via [ZeroMQ guide](http://zguide.zeromq.org/) sockets. 

This decoupling of the webserver from the request handling allows for interesting web service topologies. It also allows for easy scaling too, as servers can be added or taken down as necessary with restarting or HUPing anything.

### WSGI

Brubeck also supports WSGI. This means you can put it behind [Gunicorn](http://gunicorn.org/) or run Brubeck apps on [Heroku](http://www.heroku.com/).

WSGI support is provided by each of the concurrency options, which are described next.


## Concurrency

Brubeck is basically a pipeline of coroutines attempting to fulfill web requests.  Each `MessageHandler` is executed as a coroutine, implemented as a `greenlet`.

[Greenlet's](http://packages.python.org/greenlet/) are a Python implementation of coroutines optimized for fast context-switching.  Greenlet's can be thought of as similar to generators that don't require a `yield` statement.

Coroutines, combined with a scheduler (aka "a hub"), make for an interesting and lightweight alternative to threads.  Greenlets are so lightweight that we don't have to think too hard on how many we spawn, and Brubeck handlers each request as a single coroutine.


### Eventlet

Eventlet is an implementation of a scheduling system.  In addition to scheduling, it will convert your blocking calls into nonblocking automatically as part of it's scheduling.

This makes building nonblocking, asynchronous systems look the same as building blocking, synchronous systems. The kind that normally live in threads.

Eventlet was started by developers at Linden Labs and used to support Second Life.

Install `envs/eventlet.reqs` to use eventlet.

* [Eventlet](http://eventlet.net).
* [Eventlet History](http://eventlet.net/doc/history.html)


### Gevent

Gevent was started by Denis Bilenko as an alternative to Eventlet.  It is similar in design but uses an event loop implemented in C; `libevent`.  It will be soon be on the newer `libev`.

Tests suggest that Gevent's performance characteristics are both lightweight and very fast.

Install the `envs/gevent.reqs` to use gevent.

* [Gevent](http://gevent.org)
* [Gevent Introduction](http://gevent.org/intro.html)


### Alternatives

There are also reasonable arguments for explicit context switching.  Or perhaps even a different language.  If you prefer that model, I recommend the systems below:

* [Twisted Project](http://twistedmatrix.com/)
* [Node.js](http://nodejs.org)
* [EventMachine](https://github.com/eventmachine/eventmachine/wiki)


## DictShield

DictShield offers input validation and structuring without taking a stance on what database you should be using. There are many good reasons to use all kinds of databases. DictShield only cares about Python dictionaries. If you can get your data into those, DictShield will handle the rest. 

DictShield strives to be database agnostic in the same way that Mongrel2 is language agnostic.

* [DictShield](https://github.com/j2labs/dictshield)


