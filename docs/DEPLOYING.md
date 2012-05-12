# Deploying

Brubeck can support Mongrel2 or WSGI. 


## Mongrel2

[Mongrel2](http://mongrel2.org) is an asynchronous and language-agnostic (!) web server by [Zed Shaw](http://zedshaw.com/). Mongrel2 handles everything relevant to HTTP or Web Sockets and has facilities for passing request handling to external services via [ZeroMQ guide](http://zguide.zeromq.org/) sockets. 

This decoupling of the webserver from the request handling allows for interesting web service topologies. It also allows for easy scaling too, as servers can be added or taken down as necessary with restarting or HUPing anything.

If you are using Mongrel2, you will need to turn Mongrel2 on in addition to running a Brubeck process. This can be a little tedious while developing, but it leads to efficient production deployment capabilities similar to that of HAProxy or Nginx.

Interacting with Mongrel2 is best done with the `m2sh` command.

    $ m2sh load -config mongrel2.conf -db the.db
    $ m2sh start -db the.db -every

Mongrel2 is now running.

If you want Mongrel2 to run on port 80 you will need to use sudo. This also causes Mongrel2 to run in the background and detach from the command shell. In this case, you can stop Mongrel2 using another m2sh command.

    $ m2sh stop -db the.db -every


## WSGI

Brubeck supports WSGI by way of it's concurrency systems. This means you can put it behind [Gunicorn](http://gunicorn.org/) or run Brubeck apps on [Heroku](http://www.heroku.com/).

From an app design point of view, it is a one line change to specify a WSGI handler instead of a Mongrel2 handler.

* [Gevent WSGI](http://www.gevent.org/gevent.wsgi.html)
* [Eventlet WSGI](http://eventlet.net/doc/modules/wsgi.html)
* [Brubeck WSGI Demo](https://github.com/j2labs/brubeck/blob/master/demos/demo_wsgi.py)


## Deployment Environments

There are multiple ways to deploy Brubeck. A vanilla Ubuntu system on AWS or
Linode can work well. A Heroku dyno can work.


### Quickness

Quickness is a project for experimenting. It helps experimenters by creating
a simple environment for deploying big ideas, like Brubeck and all of it's
dependencies or Erlang or Clojure & Java & any other things worth having when
using Clojure.

It is built with Ubuntu in mind and works nicely with
[Vagrant](http://vagranup.com).

A typical Quickness install of Brubeck looks like this:

    $ git clone https://github.com/j2labs/quickness.git
    $ source quickness/env/profile
    Q: quick_new
    Q: quick_install brubeck
    
Quickness is developed by the same folks that build Brubeck & DictShield. This deployment strategy uses Mongrel2 as the web server. This involves compiling and installing both ZeroMQ and Mongrel2, but Quickness will handle all of that for you.

* [Quickness](https://github.com/j2labs/quickness)


### Heroku

To deploy to Heroku your app needs to be configured to use WSGI, which you'll see in the snippet below, and y

Install [Heroku Toolbelt](https://toolbelt.herokuapp.com/)

Prepare the project directory

	$ mkdir herokuapp && cd herokuapp

Initialize our git repo and pull Brubeck in

	$ git init
	$ git submodule add git://github.com/j2labs/brubeck.git brubeck
	$ git submodule init
	$ git submodule update

Initialize our Heroku app

	$ heroku login
	$ heroku create --stack cedar

Set up the environment

	$ virtualenv --distribute venv
	$ source venv/bin/activate
	$ pip install dictshield ujson gevent
	$ pip freeze -l > requirements.txt
 
Create .gitignore.

    $ cat .gitignore
    venv
	*.pyc
			
Create Procfile

    $ cat Procile
	web: python app.py

Create .env

    $ cat .env
	PYTHONPATH=brubeck

Create app.py

	import os

	from brubeck.request_handling import Brubeck, WebMessageHandler
	from brubeck.connections import WSGIConnection

	class DemoHandler(WebMessageHandler):
		def get(self):
			self.set_body("Hello, from Brubeck!")
			return self.render()

	config = {
		'msg_conn': WSGIConnection(int(os.environ.get('PORT', 6767))),
		'handler_tuples': [
			(r'^/', DemoHandler)
		]
	}

	if __name__ == '__main__':
		app = Brubeck(**config)
		app.run()

Try it out

    $ foreman start
    
You should now be able to visit [localhost:5000](http://localhost:5000). Notice
that this uses port 5000 instead of the usual 6767.

Is it working? Great! Let's put it on Heroku

	git add .
	git commit -m "init"
	git push heroku master

Seems like Heroku will clobber whatever PYTHONPATH you set when you first push a Python project, so set it now

	heroku config:add PYTHONPATH=/app/brubeck/:/app/

Navigate to your new Brubeck app on Heroku!


### Gunicorn

Instructions coming soon.
