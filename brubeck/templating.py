from request_handling import WebMessageHandler


def load_mako_env(template_dir, module_directory='/tmp/mako_modules',
  cache_dir=None, input_encoding='utf-8', output_encoding='utf-8',
  default_filters=['decode.utf8'], encoding_errors='replace',
  filesystem_checks=False, collection_size=512):
  """Returns a function which loads a Mako templates environment.
  """
  def loader():
    from mako.lookup import TemplateLookup
    if template_dir is not None:
      return TemplateLookup(directories=[template_dir or '.'],
        module_directory=module_directory,
        cache_dir=cache_dir,
        input_encoding=input_encoding,
        output_encoding=input_encoding,
        default_filters=default_filters,
        encoding_errors=encoding_errors,
        filesystem_checks=filesystem_checks,
        collection_size=collection_size)
    else:
      return None
  return loader
  

class MakoRendering(object):
  def render_template(self, template_file,
    _status_code=WebMessageHandler._SUCCESS_CODE, **context):
    mako_env = self.application.template_env
    template = mako_env.get_template(template_file)
    body = template.render(**context or {})
    self.set_body(body, status_code=_status_code)
    return self.render()
  
  def render_error(self, error_code):
    return self.render_template('errors.html', _status_code=error_code,
      **{'error_code': error_code})



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
    def render_template(self, template_file,
                        _status_code=WebMessageHandler._SUCCESS_CODE,
                        **context):
        """Renders payload as a jinja template
        """
        jinja_env = self.application.template_env
        template = jinja_env.get_template(template_file)
        body = template.render(**context or {})
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

def load_tornado_env(template_dir):
    """Returns a function that loads the Tornado template environment.
    """
    def loader():
        from tornado.template import Loader
        if template_dir is not None:
            return Loader(template_dir or '.')
        else:
            return None
    return loader

class TornadoRendering():
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
        tornado_env = self.application.template_env
        template = tornado_env.load(template_file)
        body = template.generate(**context or {})
        self.set_body(body, status_code=_status_code)
        return self.render()

    def render_error(self, error_code):
        """Receives error calls and sends them through a templated renderer
        call.
        """
        return self.render_template('errors.html', _status_code=error_code,
                                    **{'error_code': error_code})
