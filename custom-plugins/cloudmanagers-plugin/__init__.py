from synapse.register_plugin import register
from cloudmanagers import CloudmanagersController

os_mapping = """
[default]
default=None
"""

register(os_mapping, CloudmanagersController)
