from synapse.register_plugin import register
from directories import DirectoriesController

os_mapping = """
[default]
default=unix-directories
"""

register(os_mapping, DirectoriesController)
