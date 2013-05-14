from synapse.register_plugin import register
from rabbitmq import RabbitmqController

os_mapping = """
[default]
default=None
"""

register(os_mapping, RabbitmqController)

