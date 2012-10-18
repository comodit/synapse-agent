from synapse.resources.resources import ResourcesController
from synapse.synapse_exceptions import ResourceException

from synapse.logger import logger


@logger
class GroupsController(ResourcesController):

    __resource__ = "groups"

    def read(self, res_id=None, attributes=None):
        """
        {
            "action": "read",
            "collection": "groups",
            "id": "root"
        }

        Response: Infos about group (res_id, gid, members)
        """
        response = {}
        try:
            status = self.module.get_group_infos(res_id)
            response = self.set_response(status)

        except ResourceException, err:
            response = self.set_response("Group Error", error="%s" % err)

        if 'error' in response:
            self.logger.info('Error when reading group status %s: %s'
                    % (res_id, response['error']))

        return response

    def create(self, res_id=None, attributes=None):
        """
        {
            "action": "create",
            "collection": "groups",
            "id": "root"
            "attributes": {
                "gid": "0"
            }
        }
        """
        try:
            self.logger.info("Creating the group: %s" % res_id)
            gid = attributes.get("gid")
            self.module.group_add(res_id, gid)

            monitor = attributes.get('monitor')
            if monitor:
                item = {}
                item['present'] = True
                item['name'] = res_id
                if gid:
                    item['gid'] = gid
                self.persister.persist(self.set_response(item))

            elif monitor is False:
                item = {}
                item['present'] = False
                self.persister.unpersist(self.set_response(item))

            status = self.module.get_group_infos(res_id)
            response = self.set_response(status)
            self.logger.info("The group %s has been created" % res_id)

        except ResourceException, err:
            response = self.set_response("Group Error", error="%s" % err)

        if 'error' in response:
            self.logger.info('Error when creating group %s: %s'
                    % (res_id, response['error']))

        return response

    def update(self, res_id=None, attributes={}):
        """
        {
            "action": "update",
            "collection": "groups",
            "id": "rapha"
            "attributes": {"new_name": "raph",
                           "gid": "1001"}
        }
        """
        try:
            monitor = attributes.get('monitor')
            if monitor:
                item = {}
                item['installed'] = True
                self.persister.persist(self.set_response(item))
            elif monitor is False:
                self.persister.unpersist(self.set_response({}))

            new_name = attributes.get("new_name")
            gid = attributes.get("gid")

            status = {}
            self.logger.info("Updating the group: %s" % res_id)
            if new_name or gid:
                self.module.group_mod(res_id, new_name, gid)
                status = self.module.get_group_infos(new_name)
            else:
                status = self.module.get_group_infos(res_id)

            response = self.set_response(status)

            self.logger.info("The group %s has been updated" % res_id)

        except ResourceException, err:
            response = self.set_response("Group Error", error="%s" % err)

        if 'error' in response:
            self.logger.info('Error when updating group %s: %s'
                    % (res_id, response['error']))

        return response

    def delete(self, res_id=None, attributes=None):
        """
        {
            "action": "delete",
            "collection": "groups",
            "id": "raph"
        }
        """
        try:
            self.logger.info("Deleting the group: %s" % res_id)
            self.module.group_del(res_id)
            response = self.set_response("Successfully deleted")
            self.logger.info("The group %s has been deleted" % res_id)

        except ResourceException, err:
            response = self.set_response("Group Error", error="%s" % err)

        return response

    def monitor(self):
        """Monitors groups"""

        try:
            res = getattr(self.persister, "groups")
        except AttributeError:
            return

        response = {}
        for state in res:
            error = False
            status = state["status"]
            res_id = state["resource_id"]
            with self._lock:
                response = self.read(res_id=res_id)

            for key in status.keys():
                if response["status"].get(key) != status.get(key):
                    error = True
                    break
            if error:
                self._publish(res_id, state, response)
