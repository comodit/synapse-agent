from synapse.synapse_exceptions import ResourceException
from synapse.resources.resources import ResourcesController
from synapse.logger import logger


@logger
class GroupsController(ResourcesController):

    __resource__ = "groups"

    def read(self, res_id=None, attributes=None):
        return self.module.get_group_infos(res_id)

    def create(self, res_id=None, attributes=None):
        gid = attributes.get("gid")
        self.comply(name=res_id, present=True, gid=gid)
        self.module.group_add(res_id, gid)

        return self.module.get_group_infos(res_id)

    def update(self, res_id=None, attributes={}):
        new_name = attributes.get('new_name')
        gid = attributes.get('gid')
        monitor = attributes.get('monitor')

        self.comply(name=new_name, present=True, gid=gid, monitor=monitor)


        if self.module.exists(res_id):
            if new_name or gid:
                self.module.group_mod(res_id, new_name, gid)
                self.status = self.module.get_group_infos(new_name)
            else:
                self.status = self.module.get_group_infos(res_id)
        else:
            self.create(res_id=res_id, attributes=attributes)

        return self.status

    def delete(self, res_id=None, attributes=None):
        self.module.group_del(res_id)
        self.comply(monitor=False)
        return self.module.get_group_infos(res_id)

    def monitor(self):
        try:
            res = getattr(self.persister, "groups")
        except AttributeError:
            return

        for state in res:
            error = False
            res_status = state["status"]
            res_id = state["resource_id"]
            with self._lock:
                try:
                    self.response = self.read(res_id=res_id)
                except ResourceException as err:
                    self.logger.error(err)

            for key in res_status.keys():
                if self.response.get(key) != res_status.get(key):
                    error = True
                    break
            if error:
                self._publish(res_id, state, self.response)
