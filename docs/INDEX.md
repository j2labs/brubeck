# What Is Brubeck?

__Brubeck__ is a flexible Python web framework that aims to make the process of building scalable web services easy.

Build for scale at the same time you're prototyping your idea.


# Learn More

The [documentation](readme.html) goes into much more detail about Brubeck's design. 

You will find lots of code samples for designing request handler, authentication, cookies, and rendering templates.


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

# Brubeck.io
