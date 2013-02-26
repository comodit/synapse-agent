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

        #exec_status = self.module.exec_threaded_cmd(res_id)
        self.logger.info("Executing: %s" % res_id)
        exec_status = exec_cmd(res_id)
        if exec_status['returncode'] != 0:
            error = "Status code %s: [%s]" %(exec_status["returncode"],
                                             exec_status["stderr"])
            raise ResourceException(error)
        self.response = self.set_response(exec_status)
        self.logger.info("Done executing '%s'" % res_id)

        return self.response

    def delete(self, res_id=None, attributes=None):
        pass
