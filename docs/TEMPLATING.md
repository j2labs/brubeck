# Templates

Brubeck currently supports [Jinja2](http://jinja.pocoo.org/), [Tornado](http://www.tornadoweb.org/documentation#templates), [Mako](http://www.makotemplates.org/) or [Pystache](https://github.com/defunkt/pystache) templates.

Template support is contained in `brubeck.templates` as rendering handlers. Each handler will attach a `render_template` function to your handler and overwrite the default `render_error` to produce templated errors messages.

Using a template system is then as easy as calling `render_template` with the template filename and some context, just like you're used to.


## Jinja2 Example

Using Jinja2 template looks like this.

    from brubeck.templating import Jinja2Rendering
    
    class DemoHandler(WebMessageHandler, Jinja2Rendering):
        def get(self):
            context = {
                'name': 'J2D2',
            }
            return self.render_template('success.html', **context)
            
The corresponding HTML looks like this:

    <html>
    <head>
        <title>Jinja2 Render</title>
    </head>
    <body>
        <p>Take five, {{ name }}!</p>
    </body>
    </html>
    
* [Runnable demo](https://github.com/j2labs/brubeck/blob/master/demos/demo_jinja2.py)
* [Demo templates](https://github.com/j2labs/brubeck/tree/master/demos/templates/jinja2)


### Template Loading

In addition to using a rendering handler, you need to provide the path to your
templates.

That looks like this:

    from brubeck.templating import load_jinja2_env

    config = {
        template_loader=load_jinja2_env('./templates/jinja2')
        ...
    }

Using a function here keeps the config lightweight and flexible.
`template_loader` needs to be some function that returns an environment. 


## Demos

* Jinja2 ([Code](https://github.com/j2labs/brubeck/blob/master/demos/demo_jinja2.py), [Templates](https://github.com/j2labs/brubeck/tree/master/demos/templates/jinja2))
* Mako ([Code](https://github.com/j2labs/brubeck/tree/master/demos/demo_mako.py), [Templates](https://github.com/j2labs/brubeck/tree/master/demos/templates/mako))
* Tornado ([Code](https://github.com/j2labs/brubeck/tree/master/demos/demo_tornado.py), [Templates](https://github.com/j2labs/brubeck/tree/master/demos/templates/tornado))
* Mustache ([Code](https://github.com/j2labs/brubeck/tree/master/demos/demo_mustache.py), [Templates](https://github.com/j2labs/brubeck/tree/master/demos/templates/mustache))

Is your favorite template system not in this list? Please take a look at the other implementations. It's probably easy to add support.

* [brubeck.templating](https://github.com/j2labs/brubeck/blob/master/brubeck/templating.py)



