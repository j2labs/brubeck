# Installing The Environment

First, we have to install a few things.  Brubeck depends on Mongrel2, ZeroMQ and a few python packages.

All three packages live in github, so we'll clone the repos to our Desktop.

    $ cd ~/Desktop/
    $ git clone https://github.com/j2labs/brubeck.git
    $ git clone https://github.com/zedshaw/mongrel2.git
    $ wget http://download.zeromq.org/zeromq-2.1.7.tar.gz 
    $ tar zxf zeromq-2.1.7.tar.gz


## ZeroMQ

ZeroMQ, from a Python perspective, is actually two pieces: libzmq and pyzmq. libzmq must be installed by hand like you see below.

    $ cd ~/Desktop/zeromq-2.1.7    
    $ ./autogen.sh
    $ ./configure  ## for mac ports use: ./configure --prefix=/opt/local
    $ make 
    $ sudo make install


## Mongrel2

Mongrel2 is also painless to setup.

    $ cd ~/Desktop/mongrel2
    $ make  ## for mac ports use: make macports
    $ sudo make install

There are a few compile options available at the bottom of Mongrel2's `Makefile`. Take a look if the code above doesn't compile successfully.


## Virtualenv & Virtualenvwrapper

Brubeck works great with virtualenv. I highly recommend using it. 

Virtualenv is a way to construct isolated python environments. Very handy for managing multiple environments in a single machine.

Install both virtualenv and virtualenvwrapper with `pip`.

    pip install virtualenv virtualenvwrapper

Then, we must configure our shell to know where to store our virtualenv's. While we're there, we'll source the virtualenvwrapper shell script.

Open your `.profile` or `.bashrc` and add the following two lines.

    export WORKON_HOME="~/.virtualenvs"
    source /usr/local/bin/virtualenvwrapper

By sourcing virtualenvwrapper, you get a simple interface for creating, managing and removing virutalenv environments.

    $ mkvirtualenv <env_name> # Creates a virtual environment
    $ deactivate              # Turn off a virtual environment
    $ workon <env_name>       # Turn on a virtual environment

For more information, see my quick & dirty howto.

* [Quick & Dirty Virtualenv & Virtualenvwrapper](http://j2labs.tumblr.com/post/5181438807/quick-dirty-virtualenv-virtualenvwrapper)
    

## Python Packages & Brubeck

If you have pip installed, you can install everything with the requirements file. 

    $ cd ~/Desktop/brubeck
    $ pip install -I -r ./envs/brubeck.reqs
    
We now choose either eventlet or gevent and install the relevent requirements file in the same directory.

To install `eventlet` support:

    $ pip install -I -r ./envs/eventlet.reqs

To install `gevent` support:

    $ pip install -I -r ./envs/gevent.reqs


### Brubeck Itself

As the last step, install Brubeck.

    $ cd ~/Desktop/brubeck
    $ python setup.py install


# A Demo

Assuming the environment installation went well we can now turn on Brubeck.

First, we setup the Mongrel2 config.

    $ cd ~/Desktop/brubeck/demos
    $ m2sh load -config mongrel2.conf -db the.db
    $ m2sh start -db the.db -host localhost

Now we'll turn on a Brubeck instance.

    $ cd ~/Desktop/brubeck/demos
    $ ./demo_minimal.py

If you see `Brubeck v0.x.x online ]------------` we can try loading a URL in a browser. 
Now try [a web request](http://localhost:6767/brubeck).


## Mongrel2 Configuration

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
    
In short: any requests for `http://localhost:6767/` should be sent to the Brubeck handler. 

Don't forget that our Brubeck handler is only configured to answer `http://localhost:6767/brubeck` for now. You could add another route once you're comfortable building `MessageHandler`'s

The web server answers requests on port `6767`. It logs to the `./log` directory. It also writes a pidfile in the `./run` directory. 
