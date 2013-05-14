import re

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
        groups = self._sanitize_groups(attributes.get('groups', []))
        homedir = attributes.get('homedir') or '/home/%s' % res_id
        comment = attributes.get('full_name')
        uid = "%s" % attributes.get('uid', '') or ''
        gid = "%s" % attributes.get('gid', '') or ''
        shell = attributes.get('shell')

        self.module.user_add(res_id, password, login_group, groups,
                             homedir, comment, uid, gid, shell)

        if not uid:
            uid = self.module.get_user_infos(res_id)['uid']
        if not gid:
            gid = self.module.get_user_infos(res_id)['gid']
        if not shell:
            shell = self.module.get_user_infos(res_id)['shell']

        state = {
            'present': True,
            'password': self.module.get_pw(res_id),
            'groups': groups.append(login_group),
            'homedir': homedir,
            'gecos': comment,
            'uid': uid,
            'gid': gid,
            'shell': shell
        }
        self.save_state(res_id, state, monitor=monitor)

        return self.read(res_id)

    def update(self, res_id=None, attributes=None):

        monitor = attributes.get('monitor')
        if monitor is False:
            self.comply(monitor=False)
            return "%s unmonitored" % res_id

        password = attributes.get("password")
        login_group = attributes.get("login_group")
        groups = self._sanitize_groups(attributes.get('groups', []))
        homedir = attributes.get('homedir')
        move_home = attributes.get('move_home')
        comment = attributes.get('full_name')
        uid = "%s" % attributes.get('uid')
        gid = "%s" % attributes.get('gid')
        shell = attributes.get('shell')

        if self.module.user_exists(res_id):
            self.module.user_mod(res_id, password, login_group, groups,
                                 homedir, move_home, comment, uid, gid, shell)
            state = {
                'present': True,
                'password': self.module.get_pw(res_id),
                'groups': groups.append(login_group),
                'homedir': homedir,
                'gecos': comment,
                'uid': uid,
                'gid': gid,
                'shell': shell
            }

            self.save_state(res_id, state, monitor=monitor)

            self.response = self.module.get_user_infos(res_id)
        else:
            self.response = self.create(res_id=res_id, attributes=attributes)

        return self.read(res_id)

    def delete(self, res_id=None, attributes=None):
        monitor = attributes.get('monitor')
        state = {'present': False}
        self.save_state(res_id, state, monitor=monitor)
        self.module.user_del(res_id)
        return self.read(res_id)

    def _sanitize_groups(self, groups):
        group_list = []
        if groups:
            group_list = re.sub('\s', '', groups).split(',')
        return group_list

    def is_compliant(self, persisted_state, current_state):
        compliant = True
        name = persisted_state.get('name')

        for key in persisted_state.keys():
            if key == 'password':
                if persisted_state['password'] != self.module.get_pw(name):
                    compliant = False
            else:
                if current_state.get(key) != persisted_state[key]:
                    compliant = False

        return compliant
