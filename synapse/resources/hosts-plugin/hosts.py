from synapse.logger import logger
from synapse.resources.resources import ResourcesController
from synapse.task import OutgoingMessage, AmqpTask


@logger
class HostsController(ResourcesController):
    """ Resource exposing hosts informations.
    """

    __resource__ = "hosts"

    def read(self, res_id=None, attributes={}):
        sensors = attributes.keys()

        if not len(sensors):
            return {
                'hostname': self.module.get_hostname(),
                'ip': self.module.get_ip_addresses()
            }

        status = {}
        if 'hostname' in sensors:
            status['hostname'] = self.module.get_hostname()
        if 'ip' in sensors:
            status['ip'] = self.module.get_ip_addresses()
        if 'memtotal' in sensors:
            status['memtotal'] = self.module.get_memtotal()
        if 'macaddress' in sensors:
            status['macaddress'] = self.module.get_mac_addresses()
        if 'platform' in sensors:
            status['platform'] = self.module.get_platform()
        if 'uptime' in sensors:
            status['uptime'] = self.module.get_uptime()
        if 'cpu' in sensors:
            status['cpu'] = self.cpu()

        return status

    def ping(self):
        result = self.read()
        msg = OutgoingMessage(collection=self.__resource__,
                              status=result,
                              msg_type='status',
                              status_message=True)
        task = AmqpTask(msg)
        self.publish(task)

    def cpu(self):
        return self.module.get_cpu()

