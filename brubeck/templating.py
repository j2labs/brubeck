from request_handling import WebMessageHandler


###
### Jinja2
###

def load_jinja2_env(template_dir):
    """Returns a function that loads a jinja template environment. Uses a
    closure to provide a namespace around module loading without loading
    anything until the caller is ready.
    """
    def loader():
        from jinja2 import Environment, FileSystemLoader
        if template_dir is not None:
            return Environment(loader=FileSystemLoader(template_dir or '.'))
        else:
            return None
    return loader

class Jinja2Rendering():
    """Jinja2Rendering is a mixin for for loading a Jinja2 rendering
    environment.

    Render success is transmitted via http 200. Rendering failures result in
    http 500 errors.
    """
    def render_template(self, template_file, **context):
        """Renders payload as a jinja template
        """
        jinja_env = self.application.template_env
        template = jinja_env.get_template(template_file)
        body = template.render(**context or {})
        self.set_body(body)
        return self.render()

    def render_error(self, error_code):
        """Receives error calls and sends them through a templated renderer
        call.
        """
        return self.render_template('errors.html', **{'error_code': error_code})
