from synapse.register_plugin import register
from packages import PackagesController

os_mapping = """
[fedora]
default=yum-pkg

[centos]
default=yum-pkg

[centos_linux]
default=yum-pkg

[debian]
default=apt

[ubuntu]
default=apt

[windows]
default=win-pk
"""

register(os_mapping, PackagesController)
