from synapse.register_plugin import register
from repos import ReposController

os_mapping = """
[default]
default=yum-repos
"""

register(os_mapping, ReposController)
