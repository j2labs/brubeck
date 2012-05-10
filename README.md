# What Is Brubeck?

__Brubeck__ is a flexible Python web framework that aims to make the process of building scalable web services easy.

Brubeck's design is discussed in depth in the provided documentation. There, you will find lots of code samples for building request handlers, authentication, rendering templates, managing databases and more.


## Goals

* __Be Fast__: Brubeck is currently very fast. We intend to keep it that way.

* __Scalable__: Massive scaling capabilities should be available out of the box.

* __Friendly__: Should be easy for Python hackers of any skill level to use.

* __Pluggable__: Brubeck can speak to any language and any database.


# Example: Hello World

This is a whole Brubeck application. 

    class DemoHandler(WebMessageHandler):
        def get(self):
            self.set_body('Hello world')
            return self.render()

    urls = [(r'^/', DemoHandler)]
    msg_conn = Mongrel2Connection('ipc://127.0.0.1:9999',
                                  'ipc://127.0.0.1:9998')

    app = Brubeck(msg_conn=msg_conn,
                  handler_tuples=urls)
    app.run()


# Complete Examples

__Listsurf__ is a simple to way to save links. Yeah... another delicious clone!

It serves as a basic demonstration of what a complete site looks like when you build with Brubeck. It has authentication with secure cookies, offers a JSON API, uses [Jinja2](http://jinja.pocoo.org/) for templating and stores data in [MongoDB](http://mongodb.org).

* [Listsurf Code](https://github.com/j2labs/listsurf)

__Readify__ is a more elaborate form of Listsurf.

User's have profiles, you can mark things as liked, archived (out of your stream, kept) or you can delete them. The links can also be tagged for easy finding. This project also splits the API out from the Web system into two separate processes, each reading from a single Mongrel2.

You could actually run four Web processes and four API processes as easily as just turning each of them on four times.

This project roughly represents a typical organization of Brubeck's components. Most notably is the separation of handlers, models and queries into isolated python files.

* [Readify Code](https://github.com/j2labs/readify)

__SpotiChat__ is a chat app for spotify user.

SpotiChat provides chat for users listening to the same song with Spotify. The chat is handled via request handlers that go to sleep until incoming messages need to be distributed to connect clients. The messages are backed by [Redis](http://redis.io) too.

* [SpotiChat Code](https://github.com/sethmurphy/SpotiChat-Server)

__no.js__ is a javascript-free chat system.

It works by using the old META Refresh trick, combined with long-polling. It even works in IE4! 

* [No.js Code](https://github.com/talos/no.js)


## Contributors

Brubeck wouldn't be what it is without help from:

[James Dennis](https://github.com/j2labs), [Andrew Gwozdziewycz](https://github.com/apgwoz), [Malcolm Matalka](https://github.com/orbitz/), [Dion Paragas](https://github.com/d1on/), [Duane Griffin](https://github.com/duaneg), [Faruk Akgul](https://github.com/faruken), [Seth Murphy](https://github.com/sethmurphy), [John Krauss](https://github.com/talos), [Ben Beecher](https://github.com/gone), [Jordan Orelli](https://github.com/jordanorelli), [Michael Larsen](https://github.com/mghlarsen), [Moritz](https://github.com/m2w), [Dmitrijs Milajevs](https://github.com/dimazest), [Paul Winkler](https://github.com/slinkp), [Chris McCulloh](https://github.com/st0w), [Nico Mandery](https://github.com/nmandery), [Victor Trac](https://github.com/victortrac)


# Contact Us

If you discover bugs or want to suggest features, please use our [issue tracker](https://github.com/j2labs/brubeck/issues).

Also consider joining our mailing list: [brubeck-dev](http://groups.google.com/group/brubeck-dev).

You can find some of us in #brubeck on freenode too.
