from synapse.register_plugin import register
from repos import ReposController

os_mapping = """
[default]
default=yum-repos

[debian]
default=apt-repos
"""

register(os_mapping, ReposController)
