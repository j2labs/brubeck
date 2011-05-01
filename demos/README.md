# Demos

Each of these demo's are intended to be run as a stand alone script. But they also require installing the items in the [requirements file](../requirements.txt).


# Running it

Once your environment is ready, running it is simple:

    $ ./demo_minimal.py
    Brubeck v0.2.6 online ]-----------------------------------

Once it's online, open [localhost:6767](http://localhost:6767/) in your browser and you'll see "Take five, dude!" in your browser. You can add a GET argument `name` for [simple argument handling](http://localhost:6767/?name=j2d2).


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

