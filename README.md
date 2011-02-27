# Brubeck

Brubeck is an asynchronous, non-blocking web framework written in Python. It can also be used as an asynchronous, non-blocking message processing framework to handle the longer running jobs.

It is designed to run behind [Mongrel2](http://mongrel2.org/), but is written such that it can also be a ZeroMQ messaging framework. 

Brubeck is a system for building cloud-like API's quickly. By using Eventlet, ZeroMQ and Mongrel2 for it's concurrency, messaging and web serving Brubeck users focus exclusively on writing requests handling code.

## Goals

The most important goal is to provide a flexible, scalable web system. 

The second goal is to be agnostic of as many moving parts as possible. Mongrel2 gains language agnosticism by using ZeroMQ for interprocess communication. Brubeck does the same. Brubeck, however, takes this a step further by providing a data modeling layer that is database agnostic. 

The third goal is to provide tools that make building cloud-like API's easy. A common theme is to have a stream that can be explored via timestamps on data. That stream probably needs authentication at times. It probably needs paging too. Maybe it takes authetnicated input via HTTP POST and answers queries via HTTP GET. This should (and is!) easy to do with Brubeck.

## Example

There is a [demo app](https://github.com/j2labs/brubeck/blob/master/demo/demo.py) included with Brubeck's source code. Tornado users will notice familiar looking code.

This example code creates a handler that responds to HTTP GET. We see that because the handler implemented a function called get. 

Mongrel2 communicates with Brubeck over two local unix sockets. It could be tcp or even multicast, but the example uses ipc. 

We configure URL routing as an iterable of two-tuples. The first item is the URL pattern (/brubeck) and the second is the callable to handle this request. I like classes for handling requests, as seen in Tornado, but a simple funciton could be used if you prefer that.

    class DemoHandler(WebMessageHandler):
        def get(self):
            self.set_body('Take five!') # hello world is boring
            self.set_status(200)
            return self.render()

    pull_addr = 'ipc://127.0.0.1:9999'
    pub_addr = 'ipc://127.0.0.1:9998'

    handler_tuples = ((r'^/brubeck/$', DemoHandler),)

    app = Brubeck((pull_addr, pub_addr), handler_tuples)
    app.run()

# Code

The code is on github: [https://github.com/j2labs/brubeck](https://github.com/j2labs/brubeck).

It is also [BSD licensed](http://en.wikipedia.org/wiki/BSD_licenses).

# External packages

Brubeck reads and processes ZeroMQ messages, as sent by Mongrel2, by splitting the processing into a pipeline of [coroutines](http://en.wikipedia.org/wiki/Coroutine). 

Brubeck uses [non-blocking I/O](http://en.wikipedia.org/wiki/Asynchronous_I/O), as provided by [eventlet](http://eventlet.net/). By using Eventlet, Brubeck might be able to turn your blocking code into [non-blocking code](http://eventlet.net/doc/patching.html) automatically.

By using [DictShield](https://github.com/j2labs/dictshield), Brubeck also offers ways of interacting with user input in a structured way. DictShield offers input validation and structuring without taking a stance on what database you should be using. There are many good reasons to use all kinds of databases. DictShield only cares about Python structures, so if you can get your data into those, DictShield will handle the rest. 

## Mongrel2

Mongrel2 is an asynchronous and language-agnostic (!!) web server by [Zed Shaw](http://zedshaw.com/). Mongrel2 handles everything relevant to HTTP and has facilities for passing request handling to external services via ZeroMQ sockets. 

For a brief introduction, I will delegate to a blog post: [A Short Introduction To Mongrel2](http://j2labs.tumblr.com/post/3201232215/mongrel2-a-short-introduction).

## ZeroMQ

ZeroMQ is message passing framework that behaves like a sockets framework. Zed Shaw describes it as "sockets the way programmers think sockets work." If I need to open a TCP socket to a remote host, I simply open 'tcp://remotehost:port' and start sending messages. ZeroMQ offer easy sockets for in-process messaging, interprocess messaging, TCP or even Multicast.

You can open a socket to a host that isn't even alive and start sending it messages. ZeroMQ will queue them up and send them once that host comes online. You can configure ZeroMQ to throw an error if you'd prefer that.

By using ZeroMQ in Mongrel2, the web serving is completely separate from the request handling. It is therefore asynchronous by nature of sending a message and simply waiting for a response from some request handler.

## Eventlet

Eventlet is a concurrent networking library for Python. We get concurrency in the form of coroutines and an implicit scheduler. 

We just learned that Mongrel2 is asynchronous. Eventlet is what gives Brubeck it's asynchronicity. Async on both sides!

Eventlet offers a lot in terms of functionality so I defer to [their documentation](http://eventlet.net).

## DictShield

DictShield is Brubeck's modeling layer. DictShield allows us to structure our object models, provide validation tools and provide some thing layers of security without taking a stance on which database we use. 

Mongrel2 is language agnostic in the same way that DictShield strives to be database agnostic.

Please see [it's documentation](https://github.com/j2labs/dictshield) for more information.
