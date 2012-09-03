from synapse.register_plugin import register
from groups import GroupsController

os_mapping = """
[default]
default=unix-groups

[windows]
default=win-groups
"""

register(os_mapping, GroupsController)
