from synapse.register_plugin import register
from files import FilesController

os_mapping = """
[default]
default=unix-files

[windows]
default=win-files
"""

register(os_mapping, FilesController)
