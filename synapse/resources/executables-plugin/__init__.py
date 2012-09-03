from synapse.register_plugin import register
from executables import ExecutablesController

os_mapping = """
[default]
default=None
"""

register(os_mapping, ExecutablesController)
