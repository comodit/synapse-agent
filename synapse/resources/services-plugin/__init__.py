from synapse.register_plugin import register
from services import ServicesController

os_mapping = """
[default]
default=services-systemv

[fedora]
default=services-systemd

[debian]
default=services-debian

[ubuntu]
default=services-debian

[windows]
default=services-windows
"""

register(os_mapping, ServicesController)
