from jinja2 import Environment, FileSystemLoader

from request_handling import WebMessageHandler

class Jinja2Rendering():
    """Jinja2Rendering is a mixin for for loading a Jinja2 rendering
    environment.

    Render success is transmitted via http 200. Rendering failures result in
    http 500 errors.
    """
    @classmethod
    def load_env(cls, template_dir):
        """Returns a function that loads the template environment. 
        """
        def loader():
            if template_dir is not None:
                return Environment(loader=FileSystemLoader(template_dir or '.'))
        return loader

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
        return self.render('errors.html', **{'error_code': error_code})
    

