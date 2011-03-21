# Brubeck

Brubeck is an asynchronous, non-blocking web framework written in Python. It can also be used as an asynchronous, non-blocking message processing framework to handle the longer running jobs. In both cases, it aims to be minimal and efficient.

The code is available here: [https://github.com/j2labs/brubeck](https://github.com/j2labs/brubeck).

Brubeck is a system for building cloud-like API's quickly. By using Eventlet, ZeroMQ and Mongrel2 for it's concurrency, messaging and web serving Brubeck users focus exclusively on writing request handling code.

## Simplified look at the code

Build a request handler that answers HTTP GET requests.

    class DemoHandler(WebMessageHandler):
        def get(self):
            self.set_body('Take five!') # hello world is boring
            self.set_status(200)
            return self.render()

Set up the URL routes to load `DemoHandler` for this url: http://server/brubeck.

    handler_tuples = ((r'^/brubeck$', DemoHandler),)

Configure a Brubeck instance to connect to Mongrel2 and use our URL config. And then turn it on.

    app = Brubeck(('ipc://127.0.0.1:9999', 'ipc://127.0.0.1:9998'), handler_tuples)
    app.run()

Authentication can be provided by decorating functions, similar to Tornado.

    from brubeck.auth import web_authenticated, UserHandlingMixin

    class DemoHandler(WebMessageHandler, UserHandlingMixin):
        @web_authenticated
        def post(self):
            ...

Jinja2 templates are supported with the Jinja2Rendering Mixin.

    from brubeck.templating import Jinja2Rendering
    
    class DemoHandler(WebMessageHandler, Jinja2Rendering):
        def get(self):
            ...
            context = {
                'msg': 'This this is the context for Jinja2!',
            }
            return self.render_template('jinja.html', **context)


## Goals

* The most important goal is to provide a flexible, scalable web system.

* The second goal is to be agnostic of as many moving parts as possible. 

Mongrel2 gains language agnosticism by using ZeroMQ for socket-based communication. Brubeck does the same. Brubeck, however, takes this a step further by providing a data modeling layer that is database agnostic. 

* The third goal is to provide tools that make building cloud-like API's easy. 

A common theme is to have a stream that can be explored via timestamps on data. That stream probably needs authentication at times. It probably needs paging too. Most API's offer something along these lines, so Brubeck will too.

# Installing the environment

First, we have to install a few things. Brubeck depends on Mongrel2, ZeroMQ and a few python packages.

To stay current, I build packages from source, but I fallback to the latest tagged release. This keeps me current and avoids the compile errors the git master branches sometimes have.

Let's say, for conversation's sake, we're working from the desktop of a Mac and we are using Mac Ports. We'll first grab the necessary repos and then install them individually.

    $ cd ~/Desktop
    $ git clone https://github.com/j2labs/brubeck.git
    $ git clone https://github.com/zeromq/zeromq2.git
    $ git clone https://github.com/zeromq/pyzmq.git

## ZeroMQ

On my mac, I build packages against Mac Ports.

    $ cd ~/Desktop/zeromq2
    $ git checkout -v2.1.0
    $ ./autogen.sh
    $ ./configure --prefix=/opt/local
    $ make 
    $ make install

## Mongrel2

Zed has kept the setup for Mongrel2 very easy. On my mac, I run the following steps.

    $ cd ~/Desktop
    $ wget http://mongrel2.org/static/downloads/mongrel2-1.5.tar.bz2
    $ tar jxf mongrel2-1.5.tar.bz2
    $ cd mongrel2-1.5
    $ make macports
    $ sudo make install

## Python packages

If you have pip installed, you can use the requirements file. 

    $ cd ~/Desktop/brubeck
    $ pip install -I -r ./requirements.txt

If you don't have pip, you can easy_install the libraries listed.

People who aren't using macports can use pip to install pyzmq. 

### PyZMQ

Because I use mac ports, I have to update a config file included in the release so pyzmq knows to look in /opt/local for the zeromq libraries.

That looks like this

    $ cd ~/Desktop/pyzmq
    $ git checkout -v2.0.10
    $ cp setup.cfg.template setup.cfg
    $ vi setup.cfg # Edit file to use /opt/local instead of /usr/local
    $ python ./setup.py install

# A demo

Assuming the environment installation went well we can now turn on Brubeck.

First, we setup the Mongrel2 config.

    $ cd ~/Desktop/brubeck/demo
    $ m2sh load -config mongrel2.conf -db dev.db
    $ m2sh start --db dev.db --host localhost

Now we'll turn on a Brubeck instance.

    $ cd ~/Desktop/brubeck/demo
    $ ./demo.py

If you see `Brubeck v0.x.x online ]------------` we can try loading a URL in a browser. 
Now try (a web request)[http://localhost:6767/brubeck/].

## Web Request Example

There is a [demo app](https://github.com/j2labs/brubeck/blob/master/demo/demo.py) included with Brubeck's source code. Tornado users will notice familiar looking code.

This example code creates a handler that responds to HTTP GET. We see that because the handler implemented a function called `get()`. 

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

## Mongrel2 configuration

Mongrel2 is a separate process from Brubeck, so it is configured separately.

This is what the Mongrel2 configuration looks like for the demo project.

    brubeck_handler = Handler(
        send_spec='ipc://127.0.0.1:9999',
        send_ident='34f9ceee-cd52-4b7f-b197-88bf2f0ec378',
        recv_spec='ipc://127.0.0.1:9998', 
        recv_ident='')

    brubeck_host = Host(
        name="localhost", 
        routes={'/': brubeck_handler})
    
    brubeck_serv = Server(
        uuid="f400bf85-4538-4f7a-8908-67e313d515c2",
        access_log="/log/mongrel2.access.log",
        error_log="/log/mongrel2.error.log",
        chroot="./",
        default_host="localhost",
        name="brubeck test",
        pid_file="/run/mongrel2.pid",
        port=6767,
        hosts = [brubeck_host]
    )
    
    settings = {"zeromq.threads": 1}
    
    servers = [brubeck_serv]
    
In short, it says any requests for '/' should be sent to the Brubeck handler. To send a message to Brubeck, send down the `ipc://127.0.0.1:9999` socket. Responses from Brubeck will be received on `ipc://127.0.0.1:9998`.

The web server is answer requests on port `6767`. It's also logging into a `/log` directory and puts the processes pid in a `/run` directory.

# Licensing

Brubeck is [BSD licensed](http://en.wikipedia.org/wiki/BSD_licenses).

# External packages

Brubeck reads and processes ZeroMQ messages, as sent by Mongrel2, by splitting the processing into a pipeline of [coroutines](http://en.wikipedia.org/wiki/Coroutine). 

Brubeck uses [non-blocking I/O](http://en.wikipedia.org/wiki/Asynchronous_I/O), as provided by [eventlet](http://eventlet.net/). By using Eventlet, Brubeck might be able to turn your blocking code into [non-blocking code](http://eventlet.net/doc/patching.html) automatically.

By using [DictShield](https://github.com/j2labs/dictshield), Brubeck offers a database-agnostic, data modeling system ways of interacting with data in a structured way without taking a stance on which database system you run. DictShield offers input validation and structuring without taking a stance on what database you should be using. There are many good reasons to use all kinds of databases. DictShield only cares about Python structures, so if you can get your data into those, DictShield will handle the rest. 

## Mongrel2 + ZeroMQ

Mongrel2 is an asynchronous and language-agnostic (!!) web server by [Zed Shaw](http://zedshaw.com/). Mongrel2 handles everything relevant to HTTP and has facilities for passing request handling to external services via ZeroMQ sockets. 

Before Brubeck had been realized I covered the gist of how Mongrel2 uses ZeroMQ to fulfill requests in a blog post: [A Short Introduction To Mongrel2](http://j2labs.tumblr.com/post/3201232215/mongrel2-a-short-introduction).

I prefer the format of a blog for informal discussions of topics.

## Eventlet

Eventlet is a concurrent networking library for Python. We get concurrency in the form of coroutines and an implicit scheduler. The coroutines, which can be thought of as a replacement for threads, are very cheap. So cheap that you don't have to think too hard on how many you spawn. 

Brubeck, then, is a pipeline of coroutines attempting to fulfill web requests. By using greenlets in conjunction with a scheduler, Eventlet has the necessary pieces to handle nonblocking I/O for us. It can even monkey patch existing Python code, by providing new modules for socket, threading and others. Modules written entirely in Python likely depend on these, so Eventlet transforms them coroutine friendly at a very low level.

Eventlet is a massive library in itself, so I *defer* to (their documentation)[http://eventlet.net].

## DictShield

DictShield is Brubeck's modeling layer. DictShield allows us to structure our object models, provide validation tools and provide some thing layers of security without taking a stance on which database we use. 

Mongrel2 is language agnostic in the same way that DictShield strives to be database agnostic.

Please see [it's documentation](https://github.com/j2labs/dictshield) for more information.
