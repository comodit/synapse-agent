from synapse.resources.resources import ResourcesController
from synapse.logger import logger


@logger
class PackagesController(ResourcesController):

    __resource__ = "packages"

    def read(self, res_id=None, attributes=None):
        status = {}

        if res_id:
            status['installed'] = self.module.is_installed(res_id)
        else:
            status['installed'] = self.module.get_installed_packages()

        return status

    def create(self, res_id=None, attributes={}):
        self.check_mandatory(res_id)
        monitor = attributes.get('monitor')

        state = {'installed': True}
        self.save_state(res_id, state, monitor=monitor)

        if not self.module.is_installed(res_id):
            self.module.install(res_id)

        return self.read(res_id)

    def update(self, res_id='', attributes=None):
        self.check_mandatory(res_id)
        monitor = attributes.get('monitor')

        state = {'installed': True}
        self.save_state(res_id, state, monitor=monitor)

        self.module.update(res_id)

        return self.read(res_id)

    def delete(self, res_id=None, attributes=None):
        self.check_mandatory(res_id)
        monitor = attributes.get('monitor')

        state = {'installed': False}
        self.save_state(res_id, state, monitor=monitor)

        if self.module.is_installed(res_id):
            self.module.remove(res_id)

        return self.read(res_id)

    def is_compliant(self, expected, current):
        for key in expected.keys():
            if expected[key] != current.get(key):
                return False

        return True
