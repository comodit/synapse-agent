import os
import sys
import imp
import pkgutil

from synapse.config import config
from synapse.synapse_exceptions import ResourceException
from synapse.logger import logger
from synapse.register_plugin import registry


@logger
class ResourceLocator(object):
    def __init__(self, publish_queue):
        builtin_plugins = os.sep.join([os.path.dirname(__file__), "resources"])
        custom_plugins = config.controller['custom_plugins']
        sys.path.append(custom_plugins)
        resources_path_list = [builtin_plugins, custom_plugins]

        self.load_packages(resources_path_list)

        for controller in registry.itervalues():
            controller.publish_queue = publish_queue

    def get_instance(self, name=None):
        try:
            return registry[name] if name else registry
        except KeyError:
            raise ResourceException("The resource [%s] does not exist" % name)

    def load_packages(self, paths):
        ignored = self.get_ignored()
        for path in paths:
            for mod in pkgutil.iter_modules([path]):
                if mod[1] not in ignored:
                    fp, pathname, desc = imp.find_module(mod[1], [mod[0].path])
                    imp.load_module(mod[1], fp, pathname, desc)

    def get_ignored(self):
        # We only ignore resources specified in ignore option
        return [x.strip().lower() for x in
                config.controller['ignored_resources'].split(',')]
