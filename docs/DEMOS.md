# Learn By Example

Each demo attempts to explain some of the nuances of Brubeck.  Each example should be run from inside the [demos](https://github.com/j2labs/brubeck/blob/master/demos/) directory after Brubeck has been installed.

This document assumes you have already read the README.  If you have not, please read that and come back after.

The first two demos show the two methods of building request handlers: classes and functions.  Then we look at how URL's are handled.  Template rendering is shown for both [Jinja2](http://jinja.pocoo.org/) and [Tornado's template system](http://www.tornadoweb.org/documentation/template.html).  Finally, authentication is explained over two demos.


## Kicking Mongrel2's Tires

Each of these tests can be run underneath the same Mongrel2 instance. You can bring the handlers down and back up without taking Mongrel2 down.

First, we parse the config file into a sqlite database. Configuring the database this way makes the experience of editing configs as easy as editing text, but the database is stored in a programmatically friendly way too via [SQLite](http://www.sqlite.org/).

There is no need to edit the config so we can just load the config into a database using `m2sh load`.

    $ m2sh load -config mongrel2.conf -db dev.db
    
Now we have a sqlite database representing our config. If you have sqlite installed, open the database and take a look. You can start by typing `.tables` at the prompt to get a table list.

    $ sqlite3 dev.db 
    sqlite> .tables
    directory  host       mimetype   route      setting  
    handler    log        proxy      server     statistic
    sqlite> select * from route;
    1|/|0|1|1|handler
    2|/media/|0|1|1|dir
    
We can then turn Mongrel2 on with `m2sh start`.

    $ m2sh start -db the.db -host localhost
    ... # lots of output
    [INFO] (src/handler.c:285) Binding handler PUSH socket ipc://127.0.0.1:9999 with identity: 34f9ceee-cd52-4b7f-b197-88bf2f0ec378
    [INFO] (src/handler.c:311) Binding listener SUB socket ipc://127.0.0.1:9998 subscribed to: 
    [INFO] (src/control.c:401) Setting up control socket in at ipc://run/control
    
OK. Mongrel2 is now listening on port 6767 and sending messages down a ZeroMQ push socket, ipc://127.0.0.1:9999


### m2reader.py

Wanna see what Mongrel2 is actually saying? Turn on `m2reader.py`. It won't respond with a proper web request, but you can see the entire JSON message passed to Brubeck from Mongrel2.

    $ ./m2reader.py 
    34f9ceee-cd52-4b7f-b197-88bf2f0ec378 0 / 571:{"PATH":"/","x-forwarded-for":"127.0.0.1","accept-language":"en-US,en;q=0.8","accept-encoding":"gzip,deflate,sdch","connection":"keep-alive","accept-charset":"ISO-8859-1,utf-8;q=0.7,*;q=0.3","accept":"text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8","user-agent":"Mozilla/5.0 (Macintosh; Intel Mac OS X 10_6_8) AppleWebKit/534.30 (KHTML, like Gecko) Chrome/12.0.742.122 Safari/534.30","host":"localhost:6767","METHOD":"GET","VERSION":"HTTP/1.1","URI":"/","PATTERN":"/"},0:,
    
Brubeck's job is to send response to this request to Mongrel2, which it then then forwards to our user.


## The Demos

On the agenda:

* Classes and Functions
* URL design and handling
* Template rendering
* Authentication


# Classes And Functions

* [https://github.com/j2labs/brubeck/blob/master/demos/demo_minimal.py](https://github.com/j2labs/brubeck/blob/master/demos/demo_minimal.py)
* [https://github.com/j2labs/brubeck/blob/master/demos/demo_noclasses.py](https://github.com/j2labs/brubeck/blob/master/demos/demo_noclasses.py)

As we saw in the README there are two ways of writing message handlers.  `demo_minimal.py` implements a class that implements a `get()` function to answer HTTP GET.  `demo_noclasses.py` implements a function with it's URL mapping specified with the `add_route` decorator.


# URL Design And Handling

* [https://github.com/j2labs/brubeck/blob/master/demos/demo_urlargs.py](https://github.com/j2labs/brubeck/blob/master/demos/demo_urlargs.py)

URL's are matched by regular expression.  Sometimes parameters we need are part of the URL.  Here is a quick glance at the URL's used for this demo.

    urls = [(r'^/class/(\w+)$', NameHandler),
            (r'^/fun/(?P<name>\w+)$', name_handler),
            (r'^/', IndexHandler)]

In spite of being the last URL listed above, `IndexHandler` is the first class defined.  This class responds to HTTP GET with the string `'Take five!'`. That's it.

    class IndexHandler(WebMessageHandler):
        def get(self):
            self.set_body('Take five!')
            return self.render()

The next class, `NameHandler`, defines it's `get()` function different than `IndexHandler`.  This definition includes the parameter `name`.  Notice that in the `urls` above we asign `NameHandler` to pattern `'^/class/(\w+)$'`.  Whatever string matches `(\w+)` will be used as the value for `name`.

    class NameHandler(WebMessageHandler):
        def get(self, name):
            self.set_body('Take five, %s!' % (name))
            return self.render()

The third handler defined is not a class.  This handler is defined using the function method.  And notice that it also has a `name` argument tacked on.

    def name_handler(application, message, name):
        return http_response('Take five, %s!' % (name), 200, 'OK', {})

We put all three in the urls map and instantiate a `Brubeck` instance.  It's not running yet, but it's ready to go.

    app = Brubeck(**config)

But we'll add one more function.  We'll wrap this function with the `add_route` decorator on our app instance and map it to `'^/deco/(?P<name>\w+)$'`. This function also has the `name` variable.

    @app.add_route('^/deco/(?P<name>\w+)$', method='GET')
    def new_name_handler(application, message, name):
        return http_response('Take five, %s!' % (name), 200, 'OK', {})

Then we turn it on by calling `run()` and all four URL's can answer requests.  Try this one [http://localhost:6767/class/james](http://localhost:6767/class/james).



# Template Rendering

* [https://github.com/j2labs/brubeck/blob/master/demos/demo_jinja2.py](https://github.com/j2labs/brubeck/blob/master/demos/demo_jinja2.py)
* [https://github.com/j2labs/brubeck/blob/master/demos/demo_tornado.py](https://github.com/j2labs/brubeck/blob/master/demos/demo_tornado.py)

Template rendering is adequately covered as part of the README for now.


# Authentication

Authentication comes in many forms.  The first example will cover the basic system for authenticating requests.  The second demo will combine cookies, templates and a hard coded user to demonstrate a full login system.


## Auth Over POST

* [https://github.com/j2labs/brubeck/blob/master/demos/demo_auth.py](https://github.com/j2labs/brubeck/blob/master/demos/demo_auth.py)

To place authentication restrictions on any function you can use the `@authenticated` decorator. The purpose of this decorator is tell the web server to fail with errors sent via the relevant protocol. When using a `WebMessageHandler` errors will be sent as HTTP level errors. We will discuss another decorator `@web_authenticated` in the next section.

Here is what using it looks like.

    @authenticated
    def post(self):
        ...

For the purpose of the demonstration I hardcode a `User` instance with the username 'jd' and the password 'foo'.  Brubeck comes with a `User` and `UserProfile` model but we only use the `User` model here.

    demo_user = User.create_user('jd', 'foo')

 All `get_current_user` does is check the request arguments for a username and password and validate them.  Brubeck makes the authenticated user available for you as `self.current_user`.
 
 Let's try it using it curl.

    $ curl -d "username=jd&password=foo" localhost:6767/brubeck
    jd logged in successfully!

Now let's see it fail. We will tell curl to fail silently, meaning it won't print out any returned HTML, so we can see the 401 error Brubeck returns.

    $ curl -f -d "username=jd&password=bar" localhost:6767/brubeck
    curl: (22) The requested URL returned error: 401
    
Someone could build the first draft of an API using this example.  All errors would be passed via HTTP.


## Authenticated Website

* [https://github.com/j2labs/brubeck/blob/master/demos/demo_login.py](https://github.com/j2labs/brubeck/blob/master/demos/demo_login.py)

This example is considerably more involved.  Let's look at the URL's before we dig in.

    handler_tuples = [
        (r'^/login', LoginHandler),
        (r'^/logout', LogoutHandler),
        (r'^/', LandingHandler),
    ]
    
We can probably guess that `LoginHandler` logs a user in and `LogoutHandler` logs a user out.  But what happens if we visit [http://localhost:6767/](http://localhost:6767/) before logging in?

### Redirection

Try visiting [http://localhost:6767](http://localhost:6767) and you'll be redirected to [http://localhost:6767/login](http://localhost:6767/login). This happens because we wrapped `LoginHandler`'s `get()` method with the `@web_authenticated` decorator. 

    class LandingHandler(CustomAuthMixin, Jinja2Rendering):
        @web_authenticated
        def get(self):
            ...

Failures to pass authentication are redirected to the application's login_url, as specified in Brubeck's config.

    config = {
        ...
        'login_url': '/login',
    }

If you need to redirect a user to the login url at any point in your code, you could write the following.

    return self.redirect(self.application.login_url)

The implementation of `LoginHandler` is straight forward. The `get()` method renders the login template with fields for a username and password. The implementation of `post()` has the `@web_authenticated` decorator on it, meaning it expects auth credentials to be provided. If the credentials pass `post()` then calls `self.redirect('/')` to send a logged-in user to the landing page.


### Authentication Tracking

A cookie was set the first time `@web_authenticated` was called a cookie because we provided the correct username and password. This doesn't happen automatically. It happened because of these two lines in `get_current_user`.

    self.set_cookie('username', username) # DEMO: Don't actually put a
    self.set_cookie('password', password) # password in a cookie...

Notice the comment suggesting you shouldn't actually store a password in the cookie. This is done to keep the demo focused. Secure cookies will are covered soon..


### Authenticated Browsing

Now that we're logged in, `LandingHandler` let's us call `get()` and it renders `landing.html`. It simply says hello and offers a logout button.

Clicking logout sends us to [http://localhost:6767/logout](http://localhost:6767/logout) and `LogoutHandler` calls `self.delete_cookies()`. We are no longer authenticated so it sends us the login screen when it's finished.


### Secure Cookies

Brubeck also supports secure cookies. This is what it looks like to use them.

Setting one:

    self.set_cookie('user_id', username,
                    secret=self.application.cookie_secret)

Reading one:

    user_id = self.get_cookie('user_id',
                              secret=self.application.cookie_secret)

The [List Surf](https://github.com/j2labs/listsurf) project features secure cookies in it's authentication system.
