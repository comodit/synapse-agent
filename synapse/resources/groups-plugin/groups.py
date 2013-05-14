from synapse.resources.resources import ResourcesController
from synapse.logger import logger


@logger
class GroupsController(ResourcesController):

    __resource__ = "groups"

    def read(self, res_id=None, attributes=None):
        return self.module.get_group_infos(res_id)

    def create(self, res_id=None, attributes=None):
        monitor = attributes.get('monitor')
        gid = "%s" % attributes.get("gid")
        state = {
            'present': True,
            'gid': gid
        }
        self.save_state(res_id, state, monitor=monitor)
        self.module.group_add(res_id, gid)

        return self.read(res_id)

    def update(self, res_id=None, attributes={}):
        status = {}
        new_name = attributes.get('new_name')
        gid = "%s" % attributes.get('gid')
        monitor = attributes.get('monitor')
        state = {
            'present': True,
            'gid': gid
        }

        self.save_state(res_id, state, monitor=monitor)

        if self.module.exists(res_id):
            if new_name or gid:
                self.module.group_mod(res_id, new_name, gid)
                status = self.module.get_group_infos(new_name)
            else:
                status = self.module.get_group_infos(res_id)
        else:
            self.create(res_id=res_id, attributes=attributes)

        return self.read(res_id)

    def delete(self, res_id=None, attributes=None):
        monitor = attributes.get('monitor')
        state = {'present': False}
        self.save_state(res_id, state, monitor=monitor)
        self.module.group_del(res_id)
        return self.read(res_id)

    def is_compliant(self, persisted_state, current_state):
        compliant = True

        for key in persisted_state.keys():
            if current_state.get(key) != persisted_state.get(key):
                compliant = False
                break

        return compliant
