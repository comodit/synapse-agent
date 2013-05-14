from synapse.logger import logger
from synapse.resources.resources import ResourcesController
from synapse.task import OutgoingMessage, AmqpTask


@logger
class HostsController(ResourcesController):
    """ Resource exposing hosts informations.
    """

    __resource__ = "hosts"

    def read(self, res_id=None, attributes=None):
        return {
            'hostname': self.module.get_hostname(),
            'ip': self.module.get_ip_addresses()
        }

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

