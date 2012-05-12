# Authentication

Authentication is provided by decorating functions with the `@web_authenticated` decorator. This decorator expects the handler to have a `current_user` property that returns either an authenticated `User` model or None. 

The `UserHandlingMixin` provides functionality for authenticating a user and creating the `current_user` property. 

The work that's required will depend on how you build your system. The authentication framework uses a DictShield Document to create the `User` model, so you can implement a database query or check user information in a sorted CSV. Either way, you still get the authentication framework you need.

In practice, this is what your code looks like.

    from brubeck.auth import web_authenticated, UserHandlingMixin

    class DemoHandler(WebMessageHandler, UserHandlingMixin):
        @web_authenticated
        def post(self):
            ...

The `User` model in brubeck.auth will probably serve as a good basis for your needs. A Brubeck user looks roughly like below.

    class User(Document):
        """Bare minimum to have the concept of a User.
        """
        username = StringField(max_length=30, required=True)
        email = EmailField(max_length=100)
        password = StringField(max_length=128)
        is_active = BooleanField(default=False)
        last_login = LongField(default=curtime)
        date_joined = LongField(default=curtime)        
        ...

* [Basic Demo](https://github.com/j2labs/brubeck/blob/master/demos/demo_auth.py)
* [Login System](https://github.com/j2labs/brubeck/blob/master/demos/demo_login.py)

