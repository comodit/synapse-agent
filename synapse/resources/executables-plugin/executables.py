from synapse.syncmd import exec_cmd
from synapse.resources.resources import ResourcesController
from synapse.logger import logger
from synapse.synapse_exceptions import ResourceException


@logger
class ExecutablesController(ResourcesController):

    __resource__ = "executables"

    def read(self, res_id=None, attributes=None):
        pass

    def create(self, res_id=None, attributes=None):
        pass

    def update(self, res_id=None, attributes=None):
        if not res_id:
            raise ResourceException('Please provide a command')

        #status = self.module.exec_threaded_cmd(res_id)
        self.logger.info("Executing: %s" % res_id)
        status = exec_cmd(res_id)
        if status['returncode'] != 0:
            error = "Status code %s: [%s]" %(status["returncode"],
                                             status["stderr"])
            raise ResourceException(error)
        self.logger.info("Done executing '%s'" % res_id)

        return status

    def delete(self, res_id=None, attributes=None):
        pass
