import re

from synapse.synapse_exceptions import ResourceException
from synapse.resources.resources import ResourcesController
from synapse.logger import logger


@logger
class UsersController(ResourcesController):

    __resource__ = "users"

    def read(self, res_id=None, attributes=None):
        return self.module.get_user_infos(res_id)

    def create(self, res_id=None, attributes=None):
        password = attributes.get('password')
        login_group = attributes.get('login_group')
        groups = self.sanitize_groups(attributes.get('groups', []))
        homedir = attributes.get('homedir') or '/home/%s' % res_id
        comment = attributes.get('full_name')
        uid = attributes.get('uid')
        gid = attributes.get('gid')
        shell = attributes.get('shell')

        self.module.user_add(res_id, password, login_group, groups, 
                             homedir, comment, uid, gid, shell)

        self.comply(present=True,
                    password=self.module.get_pw(res_id),
                    groups=groups.append(login_group),
                    homedir=homedir,
                    gecos=comment,
                    uid=uid,
                    gid=gid,
                    shell=shell)

        return self.module.get_user_infos(res_id)

    def update(self, res_id=None, attributes=None):

        password = attributes.get("password")
        login_group = attributes.get("login_group")
        groups = self.sanitize_groups(attributes.get('groups', []))
        homedir = attributes.get('homedir')
        move_home = attributes.get('move_home')
        comment = attributes.get('full_name')
        uid = attributes.get('uid')
        gid = attributes.get('gid')
        shell = attributes.get('shell')
        monitor = attributes.get('monitor')

        if self.module.user_exists(res_id):
            self.module.user_mod(res_id, password, login_group, groups,
                                 homedir, move_home, comment, uid, gid, shell)

            self.comply(present=True,
                        password=self.module.get_pw(res_id),
                        groups=groups.append(login_group),
                        homedir=homedir,
                        gecos=comment,
                        uid=uid,
                        gid=gid,
                        shell=shell,
                        monitor=monitor)

            self.response = self.module.get_user_infos(res_id)
        else:
            self.response = self.create(res_id=res_id, attributes=attributes)

        return self.response

    def delete(self, res_id=None, attributes=None):
        self.comply(monitor=False)
        self.module.user_del(res_id)
        self.status['present'] = False

        return self.status

    def sanitize_groups(self, groups):
        group_list = []
        if groups:
            group_list = re.sub('\s', '', groups).split(',')
        return group_list
        
    def monitor(self):
        try:
            res = getattr(self.persister, "users")
        except AttributeError:
            return

        for state in res:
            error = False
            res_id = state["resource_id"]
            res_status = state["status"]
            with self._lock:
                try:
                    self.response = self.read(res_id=res_id)
                except ResourceException as err:
                    self.logger.error(err)

            for key in res_status.keys():
                if key == 'password':
                    if res_status['password'] != self.module.get_pw(res_id):
                        error = True
                else:
                    if self.response.get(key) != res_status[key]:
                        error = True
            if error:
                self._publish(res_id, state, self.response)
