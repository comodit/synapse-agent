from synapse.register_plugin import register
from hosts import HostsController

os_mapping = """
[default]
default=host
"""

register(os_mapping, HostsController)
