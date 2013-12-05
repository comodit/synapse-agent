from synapse.logger import logger
from synapse.resources.resources import ResourcesController
from synapse.task import OutgoingMessage, AmqpTask


@logger
class SensorsController(ResourcesController):
    """ Resource exposing sensors informations.
    """

    __resource__ = "sensors"

    def read(self, res_id=None, attributes={}):
        sensors = attributes.keys()

        self.logger.info("sensors function")

        status = {}
        if 'cpu' in sensors:
            status['cpu'] = self.cpu()

        return status

    def default(self):
        return 

    def disk_space(self, args):
	self.logger.info("disk space function:  ")
	return 156

    #def __get__(self, obj, typ=None):
    #    pass
