import os
import sys
import imp
import pkgutil

from synapse.persist import Persistence
from synapse.config import config
from synapse.synapse_exceptions import ResourceException
from synapse.logger import logger
from synapse.register_plugin import registry


@logger
class ResourceLocator(object):
    def __init__(self, scheduler, publish_queue):
        persister = Persistence()
        builtin_plugins = os.sep.join([os.path.dirname(__file__), "resources"])
        self.opts = config.controller
        custom_plugins = self.opts['custom_plugins']
        sys.path.append(custom_plugins)
        resources_path_list = [builtin_plugins, custom_plugins]

        self.load_packages(resources_path_list)

        for controller in registry.itervalues():
            controller.scheduler = scheduler
            controller.persister = persister
            controller.publish_queue = publish_queue
            controller.watch()

    def get_instance(self, name=None):
        try:
            if name:
                return registry[name]
            else:
                return registry
        except KeyError:
            raise ResourceException(
                    "The resource [{0}] does not exist".format(name))

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
                self.opts['ignored_resources'].split(',')]
