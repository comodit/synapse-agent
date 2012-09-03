from synapse.resources.resources import ResourcesController
from synapse.synapse_exceptions import ResourceException

from synapse.logger import logger


@logger
class ServicesController(ResourcesController):

    __resource__ = "services"

    def read(self, res_id=None, attributes=None):
        '''GET method retrieves the status of a service, or returns all
        services if no ID is provided. In that case, attributes can be
        provided to filter results.

        Example to retrieve the status of httpd:
        {
            "collection": "services",
            "id": "httpd",
            "action": "read"
        }

        Response:
        {
            "running": true,
            "enabled": true
        }
        '''

        status = {}
        response = {}
        try:
            if res_id is None:
                raise ResourceException('Missing ID')

            status['running'] = self.module.is_running(res_id)
            status['enabled'] = self.module.is_enabled(res_id)

            # Construct the response
            # And send it to the controller
            response = self.set_response(status)

        except ResourceException, err:
            response = self.set_response('Service Error', error='%s' % err)

        if 'error' in response:
            self.logger.info('Error when getting status of service %s: %s'
                    % (res_id, response['error']))

        return response

    def update(self, res_id=None, attributes=None):
        '''Update method can start/stop/restart and enable/disable a service.
        Id is mandatory.
        Example:
        {
        "collection": "services",
        "id": "httpd",
        "action": "POST",
        "attributes": {
            "enabled": false,
            "running": true,
            "restart": false,
            "monitor": true
            }
        }
        '''
        status = {}
        response = {}

        try:
            # Id must be provided. Update cannot be done on multiple resources.
            # Attributes key must be provided
            if res_id is None:
                raise ResourceException('Missing ID')

            if attributes is None:
                self.logger.info("Nothing to do")
                return

            enabled = attributes.get('enabled')
            running = attributes.get('running')
            restart_service = attributes.get('restart')
            reload_service = attributes.get('reload')

            # Retrieve the current state...
            status['running'] = self.module.is_running(res_id)
            status['enabled'] = self.module.is_enabled(res_id)

            # ...and compare it with desired status. Take action if different.

            #------------------------------------------------------------------
            # Enable/Disable resource
            #------------------------------------------------------------------
            if enabled is not None and enabled != status["enabled"]:
                if enabled:
                    self.logger.info("Enabling %s" % res_id)
                    self.module.enable(res_id)
                else:
                    self.logger.info("Disabling %s" % res_id)
                    self.module.disable(res_id)

            #------------------------------------------------------------------
            # Start/Stop resource
            #------------------------------------------------------------------
            if running is not None and running != status["running"]:
                if running:
                    self.logger.info("Starting %s" % res_id)
                    self.module.start(res_id)
                else:
                    self.logger.info("Stopping %s" % res_id)
                    self.module.stop(res_id)

            #------------------------------------------------------------------
            # Restart resource
            #------------------------------------------------------------------
            if restart_service:
                self.logger.info("Restarting %s" % res_id)
                self.module.restart(res_id)

            #------------------------------------------------------------------
            # Reload resource
            #------------------------------------------------------------------
            if reload_service:
                self.logger.info("Reloading %s" % res_id)
                self.module.reload(res_id)

            # Return status after actions has been taken
            status['running'] = self.module.is_running(res_id)
            status['enabled'] = self.module.is_enabled(res_id)

            # And set it in the response
            response = self.set_response(status)

            monitor = attributes.get('monitor')
            if monitor:
                item = {}
                item['enabled'] = attributes.get('enabled')
                item['running'] = attributes.get('running')
                self.persister.persist(self.set_response(item))
            elif monitor is False:
                self.persister.unpersist(self.set_response({}))

        except ResourceException, err:
            response = self.set_response('Service Error', error='%s' % err)

        if 'error' in response:
            self.logger.info('Error when updating service %s: %s'
                    % (res_id, response['error']))

        return response

    def create(self, res_id=None, attributes=None):
        return self.update(res_id=res_id, attributes=attributes)

    def delete(self, res_id=None, attributes=None):
        '''delete has no effect on a service'''
        return self.set_response("delete",
                                 error="This method has no effect.")

    def monitor(self):
        """Monitors services"""

        try:
            res = getattr(self.persister, "services")
        except AttributeError:
            return

        response = {}
        for state in res:
            res_id = state["resource_id"]
            with self._lock:
                response = self.read(res_id=res_id)
                if not response["status"] == state["status"]:
                    self._publish(res_id, state, response)
