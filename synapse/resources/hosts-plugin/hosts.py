from synapse.logger import logger
from synapse.resources.resources import ResourcesController
from synapse.synapse_exceptions import ResourceException


@logger
class HostsController(ResourcesController):
    '''Resource exposing hosts informations.'''

    __resource__ = "hosts"

    def read(self, res_id=None, attributes=None):
        self.logger.debug("Reading host informations")
        try:
            status = {}

            # Gets the hostname
            if 'hostname' in attributes:
                status['hostname'] = self.module.get_hostname()

            if 'mac' in attributes or 'mac_addresses' in attributes:
                status['mac_addresses'] = self.module.get_mac_addresses()

            if 'memtotal' in attributes:
                status['memtotal'] = self.module.get_memtotal()

            if 'ip' in attributes:
                status['ip'] = self.module.get_ip_addresses()

            if 'uptime' in attributes:
                status['uptime'] = self.module.get_uptime()

            if 'platform' in attributes:
                status['platform'] = self.module.get_platform()

            response = self.set_response(status)

        except ResourceException, err:
            response = self.set_response("Host Error", error=err)

        return response

    def monitor(self):
        """Sends hosts infos regularly."""

        attrs = ("ip", "hostname", "memtotal", "uptime")
        try:
            with self._lock:
                task = self.read(attributes=attrs)
        except ResourceException:
            pass

        if task:
            self._publish_status('', task['status'])
