# What Is Brubeck?

__Brubeck__ is a flexible Python web framework that aims to make the process of building scalable web services easy.

The [documentation](readme.html) goes into much more detail about Brubeck's design. There, you will find lots of code samples for building request handlers, authentication, rendering templates, managing databases and more.


# Example: Hello World

This is a whole Brubeck application. 

    class DemoHandler(WebMessageHandler):
        def get(self):
            self.set_body('Hello world')
            return self.render()

    urls = [(r'^/', DemoHandler)]
    mongrel2_pair = ('ipc://127.0.0.1:9999', 'ipc://127.0.0.1:9998')

    app = Brubeck(mongrel2_pair=mongrel2_pair,
                  handler_tuples=urls)
    app.run()


# Complete Example: Listsurf

__Listsurf__ is a simple to way to save links. Yeah... another delicious clone!

It serves as a basic demonstration of what a complete site looks like when you build with Brubeck. It has authentication with secure cookies, offers a JSON API, uses [Jinja2](http://jinja.pocoo.org/) for templating and stores data in [MongoDB](http://mongodb.org).

* [Listsurf on GitHub](https://github.com/j2labs/listsurf)


# Contact Us

If you discover bugs or want to suggest features, please use our [issue tracker](https://github.com/j2labs/brubeck/issues).

*NEW* You can also join the conversation on [brubeck-dev](http://groups.google.com/group/brubeck-dev).
