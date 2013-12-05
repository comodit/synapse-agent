from synapse.register_plugin import register
from sensors import SensorsController

os_mapping = """
[default]
default=None
"""

register(os_mapping, SensorsController)
