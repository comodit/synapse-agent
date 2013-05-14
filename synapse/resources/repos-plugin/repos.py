from synapse.resources.resources import ResourcesController
from synapse.logger import logger


@logger
class ReposController(ResourcesController):

    __resource__ = "repos"

    def read(self, res_id=None, attributes={}):
        res_id = self._normalize(res_id)
        details = attributes.get('details')
        return self.module.get_repos(res_id, details=details)

    def create(self, res_id=None, attributes={}):
        self.check_mandatory(res_id)
        res_id = self._normalize(res_id)
        baseurl = attributes.get('baseurl')
        monitor = attributes.get('monitor')
        state = {
            'baseurl': baseurl,
             'present': True
        }
        self.save_state(res_id, state, monitor=monitor)
        if baseurl:
            self.module.create_repo(res_id, attributes)
        return self.read(res_id)

    def update(self, res_id=None, attributes=None):
        return self.create(res_id=res_id, attributes=attributes)

    def delete(self, res_id=None, attributes=None):
        self.check_mandatory(res_id)
        monitor = attributes.get('monitor')
        res_id = self._normalize(res_id)
        state = {'present': False}
        self.save_state(res_id, state, monitor=monitor)
        self.module.delete_repo(res_id, attributes)

        return self.read(res_id)

    def is_compliant(self, persisted_state, current_state):
        compliant = True

        for key in persisted_state.keys():
            if current_state.get(key) != persisted_state[key]:
                compliant = False
                break

        return compliant

    def _normalize(self, name):
        return name.lower().replace(" ", "_")
