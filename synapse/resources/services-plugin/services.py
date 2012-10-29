from synapse.synapse_exceptions import ResourceException
from synapse.resources.resources import ResourcesController
from synapse.logger import logger


@logger
class ServicesController(ResourcesController):

    __resource__ = "services"

    def read(self, res_id=None, attributes=None):
        self.check_mandatory(res_id)
        self.status['running'] = self.module.is_running(res_id)
        self.status['enabled'] = self.module.is_enabled(res_id)

        return self.status

    def update(self, res_id=None, attributes=None):
        # Id must be provided. Update cannot be done on multiple resources.
        # Attributes key must be provided
        self.check_mandatory(res_id, attributes)

        enabled = attributes.get('enabled')
        running = attributes.get('running')
        restart_service = attributes.get('restart')
        reload_service = attributes.get('reload')
        monitor = attributes.get('monitor')

        self.comply(running=running, enabled=enabled, monitor=monitor)

        # Retrieve the current state...
        self.status['running'] = self.module.is_running(res_id)
        self.status['enabled'] = self.module.is_enabled(res_id)

        # ...and compare it with wanted status. Take action if different.

        # Enable/Disable resource
        if enabled is not None and enabled != self.status["enabled"]:
            if enabled:
                self.module.enable(res_id)
            else:
                self.module.disable(res_id)

        # Start/Stop resource
        if running is not None and running != self.status["running"]:
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
        self.status['running'] = self.module.is_running(res_id)
        self.status['enabled'] = self.module.is_enabled(res_id)

        return self.status

    def create(self, res_id=None, attributes=None):
        return self.update(res_id=res_id, attributes=attributes)

    def delete(self, res_id=None, attributes=None):
        return {}

    def monitor(self):
        """Monitors services"""

        try:
            res = getattr(self.persister, "services")
        except AttributeError:
            return

        for state in res:
            res_id = state["resource_id"]
            with self._lock:
                try:
                    self.response = self.read(res_id=res_id)
                except ResourceException as err:
                    self.logger.error(err)
                if not self.response == state["status"]:
                    self._publish(res_id, state, self.response)
                else:
                    self._publish_compliance_ok()
