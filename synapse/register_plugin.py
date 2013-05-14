import sys
import imp
import os
import ConfigParser
import StringIO
import logging

from synapse.config import config


registry = {}
log = logging.getLogger('synapse.register_plugin')


def register(mapping, cls):
    name = cls.__resource__
    if not name in registry:
        path = os.path.dirname(
                os.path.abspath(sys.modules[cls.__module__].__file__))
        if not name in registry:
            mod = get_module(mapping, path)
            registry[name] = cls(mod)


def get_module(os_mapping, dirpath):
    mapping_config = ConfigParser.RawConfigParser()
    mapping_config.readfp(StringIO.StringIO(os_mapping))
    opts = config.controller
    dist = opts['distribution_name']
    ver = opts['distribution_version']
    combinations = ((dist, ver), (dist, 'default'), ('default', 'default'))

    mod_name = None
    for comb in combinations:
        mod_name = get_module_name(mapping_config, comb[0], comb[1])
        if mod_name:
            break

    if mod_name != 'default' and mod_name is not None:
        fp, path, desc = imp.find_module(mod_name, [dirpath])
        return imp.load_module(mod_name, fp, path, desc)
    elif mod_name == 'default':
        return None


def get_module_name(conf, section='default', option='default'):
    plugin_name = None
    try:
        plugin_name = conf.get(section, option)
        if plugin_name == 'None':
            plugin_name = 'default'
    except (ConfigParser.NoSectionError, ConfigParser.NoOptionError):
        pass
    return plugin_name
