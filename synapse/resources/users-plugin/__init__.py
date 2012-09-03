from synapse.register_plugin import register
from users import UsersController

os_mapping = """
[default]
default=unix-users

[windows]
default=win-users
"""

register(os_mapping, UsersController)
