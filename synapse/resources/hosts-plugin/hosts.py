from synapse.logger import logger
from synapse.resources.resources import ResourcesController
from synapse.synapse_exceptions import ResourceException


@logger
class HostsController(ResourcesController):
    '''Resource exposing hosts informations.'''

    __resource__ = "hosts"

    def read(self, res_id=None, attributes=None):
        status = {}
        if 'hostname' in attributes:
            status['hostname'] = self.module.get_hostname()

        if 'mac' in attributes or 'mac_addresses' in attributes:
            status['mac_addresses'] = self.module.get_mac_addresses()

        if 'memtotal' in attributes:
            status['memtotal'] = self.module.get_memtotal()

        if 'cpu' in attributes:
            status['cpu'] = self.module.get_cpu()

        if 'ip' in attributes:
            status['ip'] = self.module.get_ip_addresses()

        if 'uptime' in attributes:
            status['uptime'] = self.module.get_uptime()

        if 'platform' in attributes:
            status['platform'] = self.module.get_platform()

        return status

    def watch(self):
        interval = self._get_monitor_interval()
        self.add_job(interval)

    def monitor(self):
        """Sends hosts infos regularly."""

        try:
            attrs = ("ip", "hostname", "memtotal", "uptime")
            self._publish_status('', self.read(attributes=attrs))
        except ResourceException:
            pass
