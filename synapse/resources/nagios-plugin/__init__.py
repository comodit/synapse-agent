from synapse.register_plugin import register
from nagios import NagiosPluginsController

os_mapping = """
[default]
default=None
"""

register(os_mapping, NagiosPluginsController)

