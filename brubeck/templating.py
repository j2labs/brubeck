from request_handling import WebMessageHandler


###
### Mako templates
###

def load_mako_env(template_dir, *args, **kwargs):
    """Returns a function which loads a Mako templates environment.
    """
    def loader():
        from mako.lookup import TemplateLookup
        if template_dir is not None:
            return TemplateLookup(directories=[template_dir or '.'],
                                  *args, **kwargs)
        else:
            return None
    return loader


class MakoRendering(WebMessageHandler):
    def render_template(self, template_file,
                        _status_code=WebMessageHandler._SUCCESS_CODE,
                        **context):
        body = self.application.render_template(template_file, **context or {})
        self.set_body(body, status_code=_status_code)
        return self.render()

    def render_error(self, error_code):
        return self.render_template('errors.html', _status_code=error_code,
                                    **{'error_code': error_code})


###
### Jinja2
###

def load_jinja2_env(template_dir, *args, **kwargs):
    """Returns a function that loads a jinja template environment. Uses a
    closure to provide a namespace around module loading without loading
    anything until the caller is ready.
    """
    def loader():
        from jinja2 import Environment, FileSystemLoader
        if template_dir is not None:
            return Environment(loader=FileSystemLoader(template_dir or '.'),
                               *args, **kwargs)
        else:
            return None
    return loader


class Jinja2Rendering(WebMessageHandler):
    """Jinja2Rendering is a mixin for for loading a Jinja2 rendering
    environment.

    Render success is transmitted via http 200. Rendering failures result in
    http 500 errors.
    """
    def render_template(self, template_file,
                        _status_code=WebMessageHandler._SUCCESS_CODE,
                        **context):
        """Renders payload as a jinja template
        """
        body = self.application.render_template(template_file, **context or {})
        self.set_body(body, status_code=_status_code)
        return self.render()

    def render_error(self, error_code):
        """Receives error calls and sends them through a templated renderer
        call.
        """
        return self.render_template('errors.html', _status_code=error_code,
                                    **{'error_code': error_code})


###
### Tornado
###

def load_tornado_env(template_dir, *args, **kwargs):
    """Returns a function that loads the Tornado template environment.
    """
    def loader():
        from tornado.template import Loader
        if template_dir is not None:
            return Loader(template_dir or '.', *args, **kwargs)
        else:
            return None
    return loader


class TornadoRendering(WebMessageHandler):
    """TornadoRendering is a mixin for for loading a Tornado rendering
    environment.

    Follows usual convention: 200 => success and 500 => failure

    The unusual convention of an underscore in front of a variable is used
    to avoid conflict with **context. '_status_code', for now, is a reserved
    word.
    """
    def render_template(self, template_file,
                        _status_code=WebMessageHandler._SUCCESS_CODE,
                        **context):
        """Renders payload as a tornado template
        """
        body = self.application.render_template(template_file, **context or {})
        self.set_body(body, status_code=_status_code)
        return self.render()

    def render_error(self, error_code):
        """Receives error calls and sends them through a templated renderer
        call.
        """
        return self.render_template('errors.html', _status_code=error_code,
                                    **{'error_code': error_code})

###
### Mustache
###

def load_mustache_env(template_dir, *args, **kwargs):
    """
    Returns a function that loads a mustache template environment. Uses a
    closure to provide a namespace around module loading without loading
    anything until the caller is ready.
    """
    def loader():
        import pystache

        return pystache.Renderer(search_dirs=[template_dir])

    return loader


class MustacheRendering(WebMessageHandler):
    """
    MustacheRendering is a mixin for for loading a Mustache rendering
    environment.

    Render success is transmitted via http 200. Rendering failures result in
    http 500 errors.
    """
    def render_template(self, template_file,
                        _status_code=WebMessageHandler._SUCCESS_CODE,
                        **context):
        """
        Renders payload as a mustache template
        """
        mustache_env = self.application.template_env

        template = mustache_env.load_template(template_file)
        body = mustache_env.render(template, context or {})

        self.set_body(body, status_code=_status_code)
        return self.render()

    def render_error(self, error_code):
        """Receives error calls and sends them through a templated renderer
        call.
        """
        return self.render_template('errors', _status_code=error_code,
                                    **{'error_code': error_code})
