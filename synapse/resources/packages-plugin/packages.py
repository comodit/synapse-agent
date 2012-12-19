from synapse.resources.resources import ResourcesController
from synapse.logger import logger


@logger
class PackagesController(ResourcesController):

    __resource__ = "packages"

    def read(self, res_id=None, attributes=None):
        if res_id:
            self.status['installed'] = self.module.is_installed(res_id)
        else:
            self.status['installed'] = self.module.get_installed_packages()

        return self.status

    def create(self, res_id=None, attributes={}):
        self.check_mandatory(res_id)

        self.comply(installed=True)

        if not self.module.is_installed(res_id):
            self.module.install(res_id)

        self.status['installed'] = self.module.is_installed(res_id)

        return self.status

    def update(self, res_id='', attributes=None):
        if res_id:
            monitor = attributes.get('monitor')
            self.comply(installed=True, monitor=monitor)
            self.module.update(res_id)
            self.status['installed'] = self.module.is_installed(res_id)

        return self.status

    def delete(self, res_id=None, attributes=None):
        self.check_mandatory(res_id)

        self.comply(monitor=False)

        if self.module.is_installed(res_id):
            self.module.remove(res_id)

        return self.status

    def monitor(self, persisted_state, current_state):
        compliant = True

        for key in persisted_state.keys():
            if current_state.get(key) != persisted_state.get(key):
                compliant = False
                break

        return compliant
