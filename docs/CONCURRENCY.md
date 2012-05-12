# Concurrency

Brubeck is basically a pipeline of coroutines attempting to fulfill web requests.  Each `MessageHandler` is executed as a coroutine. [Greenlet's](http://packages.python.org/greenlet/), the coroutines in Brubeck, are optimized for fast context-switching.  

Coroutines, combined with a scheduler (aka "a hub"), make for an interesting and lightweight alternative to threads.  Greenlets are so lightweight that we don't have to think too hard on how many we spawn, and Brubeck handles each request as a single coroutine.

Brubeck supports Eventlet and Gevent. They are similar in design. Both use Greenlets for coroutines. Both provide a mechanism for converting blocking network drivers into nonblocking. They both provide a schedular, aka a "hub", to provide *thread-like* behavior.


## The Flow

Processing flows from the incoming message to a function that processes that message into the form of a `Request`. This request will operate until it reaches some point of I/O, or, it completes.

Brubeck has a scheduler, like Twisted's Reactor or Tornado's IOLoop, but it's behind the scenes. Being behind the scenes allows it to create a simple interface to nonblocking behavior, but can be confusing upfront.

If you're reaching out to the database, Brubeck might go back and check for incoming messages. If you're reaching out to some http service, Brubeck might check for incoming messages, or complete that other request that now has data from the database. In this sense, the context switching is *implicit*.

Brubeck can offer nonblocking access to:

* SSH w/ [paramiko](http://www.lag.net/paramiko/)
* MySQL
* Postgres
* Redis w/ [redis-py](https://github.com/andymccurdy/redis-py)
* MongoDB w/ [pymongo](http://api.mongodb.org/python/current/)
* Riak w/ [riak](https://github.com/basho/riak-python-client)
* Memcache


## Gevent

Gevent was started by Denis Bilenko and is written to use `libevent`. Gevent's performance characteristics suggest it is very fast, stable and efficient on resources.

Install the `envs/gevent.reqs` to use gevent.

* [Gevent](http://gevent.org)
* [Gevent Introduction](http://gevent.org/intro.html)

Extras:

* MySQL w/ [ultramysql](https://github.com/esnme/ultramysql)
* Postgres w/ [psychopg](http://wiki.postgresql.org/wiki/Psycopg)
* Memcache w/ [ultramemcache](https://github.com/esnme/ultramemcache)


## Eventlet

Eventlet is distinct for being mostly in Python.  It later added support for libevent too.  Eventlet was started by developers at Linden Labs and used to support Second Life.

Install `envs/eventlet.reqs` to use eventlet.

* [Eventlet](http://eventlet.net).
* [Eventlet History](http://eventlet.net/doc/history.html)

Extras:

* [Database Connection Pooling](http://eventlet.net/doc/modules/db_pool.html)


## Making A Decision

I tend to choose gevent.  My tests have shown that it is significantly faster and lighter on resources than Eventlet. 

If you have virtualenv, try experimenting and seeing which one you like best.
