# Brubeck Demos

Each of these demo's are intended to be run as a stand alone script. But they also require installing the items in the [requirements file](../requirements.txt).


# Running it

Once your environment is ready, running it is simple:

    $ ./demo_minimal.py
    Brubeck v0.2.6 online ]-----------------------------------

This is Brubeck, we must also turn on Mongrel2.

    $ m2sh load -config mongrel2.conf -db dev.db
    $ m2sh start --db dev.db --host localhost

OK, Mongrel2 is up. That's both pieces, so open [localhost:6767](http://localhost:6767/) in your browser and you'll see "Take five, dude!". 

# Coding for Brubeck

In general, the experience of coding for Brubeck is:

1. Write a message handler
2. Configure your Brubeck instance
3. Call `run()`

People familiar with Tornado will recognize the general feel of writing a `WebMessageHandler`.


## demo_minimal.py

This a Brubeck's *hello world*. It demonstrates building a Handler that responds to HTTP GET. 

Let's look at the code.

    #!/usr/bin/env python
    
    import sys
    from brubeck.request_handling import Brubeck, WebMessageHandler
    
    class DemoHandler(WebMessageHandler):
        def get(self):
            name = self.get_argument('name', 'dude')
            self.set_body('Take five, %s!' % name)
            return self.render()
    
    config = {
        'mongrel2_pair': ('ipc://127.0.0.1:9999', 'ipc://127.0.0.1:9998'),
        'handler_tuples': [(r'^/$', DemoHandler)],
    }
    app = Brubeck(**config)
    app.run()


### Code a Handler

On line 6 we subclass `WebMessageHandler` to create `DemoHandler`. By implementing a funciton called `get()` on line 8, we are telling our handler to respond to HTTP GET.


### Configure the Brubeck instance

Below `DemoHandler` is a dictionary called `config` with two keys: `mongrel2_pair` and `handler_tuples`.

`mongrel2_pair` represents our config for talking to Mongrel2. Mongrel2 sends Brubeck a message on the first socket, we process it, we send our response back on the second socket.

`handler_tuples` is a list of handler's and a regex to match for calling them. In this example, the DemoHandler responds to `^/$`. With the demo Mongrel2 config, this means `localhost:6767/`. 


### Call `run()`

The code then passes the config to instantiate a `Brubeck` and it calls `run()`. 

Brubeck is online!


## demo_login.py

After trying the minimal demo, I recommend trying the login demo. This demo uses Jinja2 templates and cookies to track a user logged into the site. You can login using username: `jd` and password: `foo`, as hardcoded in `demo_login.py`.

    $ ./demo_login.py
    Brubeck v0.2.6 online ]-----------------------------------

When you visit `localhost:6767/`, you will be redirected to `localhost:6767/login`. Once you login, you will be redirected back to `localhost:6767/` but this time you will see "Hello!" and a logout button.


# Preparing the environment.

The requirements might seem a little daunting... Sorry about that. Brubeck is standing on the shoulders of a few giants and those giants come in the form of Python and C code.

If you have pip installed, handling the requirements is easy. 

    pip install -I -r brubeck/etc/requirements.txt

If you don't have pip, [you should check it out](http://pypi.python.org/pypi/pip).

    easy_install pip

For a more extensive discussion of the install, see the [install guide](https://github.com/j2labs/brubeck/blob/master/docs/INSTALLING.md)


## VirtualEnv

To make managing my Python environment easier, I use multiple *virtual* environments with virtualenv. I can install whole Python environments and delete them from my system with two easy commands: `mkvirtualenv` and `rmvirtualenv`. 

For more information, try [this blog post](http://jontourage.com/2011/02/09/virtualenv-pip-basics/) from Jonathan Chu.

