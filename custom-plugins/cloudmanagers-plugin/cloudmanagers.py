from synapse.resources.resources import ResourcesController
from synapse.synapse_exceptions import ResourceException

from synapse.logger import logger


@logger
class CloudmanagersController(ResourcesController):

    __resource__ = "cloudmanagers"

    def read(self, res_id=None, attributes=None):
        pass

    def create(self, res_id=None, attributes={}):
        pass

    def update(self, res_id=None, attributes=None):
        pass

    def delete(self, res_id=None, attributes=None):
        pass
