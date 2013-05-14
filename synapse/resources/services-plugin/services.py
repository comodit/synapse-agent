from synapse.synapse_exceptions import ResourceException
from synapse.resources.resources import ResourcesController
from synapse.logger import logger


@logger
class ServicesController(ResourcesController):

    __resource__ = "services"

    def read(self, res_id=None, attributes=None):
        status = {}
        self.check_mandatory(res_id)
        status['running'] = self.module.is_running(res_id)
        status['enabled'] = self.module.is_enabled(res_id)

        return status

    def create(self, res_id=None, attributes=None):
        return self.update(res_id=res_id, attributes=attributes)

    def update(self, res_id=None, attributes=None):
        # Id must be provided. Update cannot be done on multiple resources.
        # Attributes key must be provided
        status = {}
        self.check_mandatory(res_id, attributes)
        monitor = attributes.get('monitor')

        enabled = attributes.get('enabled')
        running = attributes.get('running')
        restart_service = attributes.get('restart')
        reload_service = attributes.get('reload')
        monitor = attributes.get('monitor')

        state = {
            'running': running,
            'enabled': enabled
        }

        self.save_state(res_id, state, monitor=monitor)

        # Retrieve the current state...
        status['running'] = self.module.is_running(res_id)
        status['enabled'] = self.module.is_enabled(res_id)

        # ...and compare it with wanted status. Take action if different.

        # Enable/Disable resource
        if enabled is not None and enabled != status["enabled"]:
            if enabled:
                self.module.enable(res_id)
            else:
                self.module.disable(res_id)

        # Start/Stop resource
        if running is not None and running != status["running"]:
            if running:
                self.module.start(res_id)
            else:
                self.module.stop(res_id)

        # Restart resource
        if restart_service:
            self.module.restart(res_id)

        # Reload resource
        if reload_service:
            self.module.reload(res_id)

        # Return status after actions has been taken
        status['running'] = self.module.is_running(res_id)
        status['enabled'] = self.module.is_enabled(res_id)

        return status

    def delete(self, res_id=None, attributes=None):
        return {}

    def is_compliant(self, persisted_state, current_state):
        compliant = True

        for key in persisted_state.keys():
            if current_state.get(key) != persisted_state.get(key):
                compliant = False
                break

        return compliant
