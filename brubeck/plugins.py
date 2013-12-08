"""Basically anything can use plugins because plugins are just a mechanism for
attaching python modules to the Brubeck environment.  This is how opinions can
remain outside of Brubeck while still being a core piece of someone's
experience.

This is good for creativity.

But, anything, really, could be a pluggable, so the code is written such that
you could use it with anything.
"""

###
### Exceptions
###

class PluginException(Exception):
    pass

class MalformedPluginException(Exception):
    pass


###
### Plugin Body
###

class Plugin(object):
    def __init__(self, *a, **kw):
        """Here, for now, primarily to tell plugin authors to call super.
        """
        super(Plugin, self).__init__(*a, **kw)

    def init_plugin(self):
        raise NotImplementedException('init_plugin must be overridden')
            
    def teardown_plugin(self):
        raise NotImplementedException('teardown_plugin must be overridden')


###
### Plugin Host
###

class PluginsProxy(object):
    pass


class Pluggable:
    """Pluggable is a mixin that provides functions and data for working with
    plugins.
    """
    @property
    def plugins(self):
        if not hasattr(self, '_plugins'):
            self._plugins = PluginsProxy()
        return self._plugins

    def activate_plugin(self, plugin, *a, **kw):
        """Installs a plugin in the host class and prepares it for use.
        """
        self._audit_plugin(plugin)
        plugin.init_plugin(self, *a, **kw)
        plugin_name = self._extract_plugin_name(plugin.__class__.__name__)
        setattr(self.plugins, plugin_name, plugin)

    def deactivate_plugin(self, plugin):
        """Uninstalls a plugin from host class
        """
        plugin.terminate_plugin(self)
        plugin_name = self._extract_plugin_name(plugin.__class__.__name__)
        delattr(self.plugins, plugin_name)

    @staticmethod
    def _extract_plugin_name(name):
        """Takes a class name, like `Jinja2Plugin` and returns 'jinja2'.
        """
        name_lowered = name.lower()
        if not 'plugin' in name_lowered:
            raise MalformedPluginException('Class not identified as plugin')
        return name_lowered.replace('plugin', '')

    @staticmethod
    def _audit_plugin(plugin):
        """Does a quick check to make sure the thing implements the necessary
        functions to be a plugin.
        """
        if not hasattr(plugin, 'init_plugin'):
            raise MalformedPluginException("Missing 'init_plugin'")
        if not hasattr(plugin, 'teardown_plugin'):
            raise MalformedPluginException("Missing 'teardown_plugin'")

