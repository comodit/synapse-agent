import re

from synapse.resources.resources import ResourcesController
from synapse.synapse_exceptions import ResourceException
from synapse.logger import logger


@logger
class UsersController(ResourcesController):

    __resource__ = "users"

    def read(self, res_id=None, attributes=None):
        """
        Gets information about user.
        {
            "action": "read",
            "collection": "users",
            "id": "root"
        }

        Response: Infos about user (gid, uid, name, dir, shell, gecos, groups)
        """
        try:
            status = self.module.get_user_infos(res_id)
            response = self.set_response(status)

        except ResourceException, err:
            response = self.set_response({}, error="%s" % err)

        return response

    def create(self, res_id=None, attributes=None):
        """
        Creates a user.
        Attributes: -password: clear password
                    -login_group: main user group
                    -groups: additional groups the user is in, comma separated
        {
            "action": "create",
            "collection": "users",
            "id": "raph"
            "attributes": {
                "password": "secret",
                "login_group": "raph",
                "groups": "mock,wheel",
                "homedir": "/home/raph",
                "full_name": "Raphael De Giusti",
                "uid": "uid",
                "gid": "gid",
                "shell": "shell",
                }
        }
        """
        response = {}
        try:
            self.logger.info("Creating the user '%s'" % res_id)
            password = attributes.get('password')
            login_group = attributes.get('login_group') or res_id
            groups = self.sanitize_groups(attributes.get('groups', []))
            homedir = attributes.get('homedir') or '/home/%s' % res_id
            comment = attributes.get('full_name') or ''
            uid = attributes.get('uid')
            gid = attributes.get('gid')
            shell = attributes.get('shell')

            self.module.user_add(res_id, password, login_group, groups, 
                                 homedir, comment, uid, gid, shell)

            monitor = attributes.get('monitor')
            if monitor:
                item = {}
                item['present'] = True
                item['name'] = res_id
                if password:
                    item['password'] = self.module.get_pw(res_id)
                item['groups'] = [login_group]
                if groups:
                    item['groups'] += groups
                if homedir:
                    item['homedir'] = homedir
                if comment:
                    item['comment'] = comment
                if uid:
                    item['uid'] = uid
                if gid:
                    item['gid'] = gid
                if shell:
                    item['shell'] = shell
                self.persister.persist(self.set_response(item))

            elif monitor is False:
                item = {}
                item['present'] = False
                self.persister.unpersist(self.set_response(item))

            status = self.module.get_user_infos(res_id)
            response = self.set_response(status)
            self.logger.info("The user '%s' has been created" % res_id)

        except ResourceException, err:
            status = {}
            status['present'] = False
            response = self.set_response(status, error="%s" % err)

        if 'error' in response:
            self.logger.info("Error when creating user '%s': %s"
                    % (res_id, response['error'].strip()))

        return response

    def update(self, res_id=None, attributes=None):
        """
        Updates a user.
        Attributes: -password: password in plain text
                    -login_group: main user group
                    -add_to_groups: add user to groups. Will append new groups
                    -remove_from_groups: removes user from groups.
                    -set_groups: Resets then set groups for user
        {
            "action": "update",
            "collection": "users",
            "id": "raph"
            "attributes": {
                "password": "newsecret",
                "remove_from_groups": "wheel",
                }
        }
        """

        self.logger.info("Updating the user: %s" % res_id)
        password = attributes.get("password")
        login_group = attributes.get("login_group")
        groups = self.sanitize_groups(attributes.get('groups', []))
        homedir = attributes.get('homedir')
        move_home = attributes.get('move_home')
        comment = attributes.get('full_name')
        uid = attributes.get('uid')
        gid = attributes.get('gid')
        shell = attributes.get('shell')

        try:
            self.module.user_mod(res_id, password, login_group, groups,
                                 homedir, move_home, comment, uid, gid, shell)

            monitor = attributes.get('monitor')
            if monitor:
                item = {}
                item['present'] = True
                item['name'] = res_id
                item['password'] = self.module.get_pw(res_id)
                item['groups'] = groups.append(login_group)
                item['homedir'] = homedir
                item['gecos'] = comment
                item['uid'] = uid
                item['gid'] = gid
                item['shell'] = shell
                self.persister.persist(self.set_response(item))
            elif monitor is False:
                item = {}
                item['present'] = False
                self.persister.unpersist(self.set_response(item))

            status = self.module.get_user_infos(res_id)
            response = self.set_response(status)
            self.logger.info("The user '%s' has been updated" % res_id)

        except ResourceException, err:
            response = self.set_response("User Error", error="%s" % err)

        if 'error' in response:
            self.logger.info("Error when updating user '%s': %s"
                    % (res_id, response['error'].strip()))

        return response

    def delete(self, res_id=None, attributes=None):
        """
        Deletes a user with the force flag.
        {
            "action": "delete",
            "collection": "users",
            "id": "raph"
        }
        """
        try:
            self.logger.info("Deleting the user: %s" % res_id)
            self.module.user_del(res_id)

            monitor = attributes.get('monitor')
            if monitor:
                item = {}
                item['present'] = True
                self.persister.persist(self.set_response(item))
            elif monitor is False:
                item = {}
                self.persister.unpersist(self.set_response(item))

            response = self.set_response("Successfully deleted")
            self.logger.info("The user '%s' has been deleted" % res_id)

        except ResourceException, err:
            response = self.set_response("User Error", error="%s" % err)

        if 'error' in response:
            self.logger.info("Error when deleting user '%s': %s"
                    % (res_id, response['error'].strip()))

        return response

    def sanitize_groups(self, groups):
        group_list = []
        if groups:
            group_list = re.sub('\s', '', groups).split(',')
        return group_list
        
    def monitor(self):
        """Monitors users"""

        try:
            res = getattr(self.persister, "users")
        except AttributeError:
            return

        response = {}
        for state in res:
            error = False
            res_id = state["resource_id"]
            status = state["status"]
            with self._lock:
                response = self.read(res_id=res_id)

            for key in status.keys():
                if key == 'password':
                    if status['password'] != self.module.get_pw(res_id):
                        error = True
                else:
                    if response['status'].get(key) != status[key]:
                        error = True
            if error:
                self._publish(res_id, state, response)
