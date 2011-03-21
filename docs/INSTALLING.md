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

    $ cd ~/Desktop/brubeck/demos
    $ ./demo_minimal.py

If you see `Brubeck v0.x.x online ]------------` we can try loading a URL in a browser. 
Now try (a web request)[http://localhost:6767/brubeck/].

## Web Request Example

There is a [demo app](https://github.com/j2labs/brubeck/blob/master/demo/demo_minimal.py) included with Brubeck's source code. Tornado users will notice a familiar looking design.

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

    handler_tuples = [(r'^/brubeck', DemoHandler)]

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
        hosts = [brubeck_host])
    
    settings = {"zeromq.threads": 1}
    
    servers = [brubeck_serv]
    
In short, it says any requests for '/' should be sent to the Brubeck handler. 

Did you notice that Brubeck is configured to answer /brubeck, but Mongrel2 will send all web requests to Brubeck? Try a URL that Brubeck isn't ready for to see how it errors.

The web server is answer requests on port `6767`. It's also logging into a `/log` directory and puts the processes pid in a `/run` directory.
