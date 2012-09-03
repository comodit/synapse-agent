from synapse.syncmd import exec_cmd
from synapse.resources.resources import ResourcesController
from synapse.logger import logger
from synapse.synapse_exceptions import ResourceException


@logger
class ExecutablesController(ResourcesController):

    __resource__ = "executables"

    def read(self, res_id=None, attributes=None):
        pass
        #try:
        #    if not res_id:
        #        raise ResourceException('Please provide a command')

        #    self.module.exec_cmd(res_id)

        #    out = self.module.__STDOUTBUF__
        #    err = self.module.__STDERRBUF__

        #    if not err:
        #        response = self.set_response(out)
        #    else:
        #        response = self.set_response(err)
        #except ResourceException, err:
        #    status = dict()
        #    response = self.set_response(status, error='{0}'.format(err))

        #return response

    def update(self, res_id=None, attributes=None):
        try:
            if not res_id:
                raise ResourceException('Please provide a command')

            #exec_status = self.module.exec_threaded_cmd(res_id)
            self.logger.info("Executing: %s" % res_id)
            exec_status = exec_cmd(res_id)
            response = self.set_response(exec_status)
            self.logger.info("Done executing '%s'" % res_id)

        except ResourceException, err:
            response = self.set_response('Exec error', error='%s' % err)

        if 'error' in response:
            self.logger.info('Error when executing the command %s: %s'
                    % (res_id, response['error']))

        return response

    def delete(self, res_id=None, attributes=None):
        pass
