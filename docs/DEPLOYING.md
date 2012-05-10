# Deploying

Brubeck can support Mongrel2 or WSGI. 


## Mongrel2

[Mongrel2](http://mongrel2.org) is an asynchronous and language-agnostic (!) web server by [Zed Shaw](http://zedshaw.com/). Mongrel2 handles everything relevant to HTTP or Web Sockets and has facilities for passing request handling to external services via [ZeroMQ guide](http://zguide.zeromq.org/) sockets. 

This decoupling of the webserver from the request handling allows for interesting web service topologies. It also allows for easy scaling too, as servers can be added or taken down as necessary with restarting or HUPing anything.


## WSGI

Brubeck supports WSGI by way of it's concurrency system. This means you can put it behind [Gunicorn](http://gunicorn.org/) or run Brubeck apps on [Heroku](http://www.heroku.com/).

* [Gevent WSGI](http://www.gevent.org/gevent.wsgi.html)
* [Eventlet WSGI](http://eventlet.net/doc/modules/wsgi.html)


## Gunicorn

Instructions coming soon.


## Heroku

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

10. Try it out

    $ foreman start
    
You should now be able to visit [localhost:5000](http://localhost:5000)

11. Is it working? Great! Let's put it on Heroku

	git add .
	git commit -m "init"
	git push heroku master

Seems like Heroku will clobber whatever PYTHONPATH you set when you first push a Python project, so set it now

	heroku config:add PYTHONPATH=/app/brubeck/:/app/

Navigate to your new Brubeck app on Heroku!
