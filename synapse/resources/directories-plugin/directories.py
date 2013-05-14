import getpass
from datetime import datetime

from synapse.resources.resources import ResourcesController
from synapse.logger import logger
from synapse.synapse_exceptions import ResourceException


@logger
class DirectoriesController(ResourcesController):

    __resource__ = "directories"

    def read(self, res_id=None, attributes={}):
        status = {}
        self.check_mandatory(res_id)

        present = self.module.is_dir(res_id)
        status['present'] = present
        if present:
            status['owner'] = self.module.owner(res_id)
            status['group'] = self.module.group(res_id)
            status['mode'] = self.module.mode(res_id)
            status['mod_time'] = self.module.mod_time(res_id)
            status['c_time'] = self.module.c_time(res_id)

        return status

    def create(self, res_id=None, attributes={}):
        self.check_mandatory(res_id)
        monitor = attributes.get('monitor')

        owner = self._get_owner(res_id, attributes)
        group = self._get_group(res_id, attributes)
        mode = self._get_mode(res_id, attributes)

        state = {
            'owner': owner,
            'group': group,
            'mode': mode,
            'mod_time': str(datetime.now()),
            'c_time': str(datetime.now()),
            'present': True
        }
        self.save_state(res_id, state, monitor=monitor)

        self.module.create_folders(res_id)

        # Update meta of given file
        self.module.update_meta(res_id, owner, group, mode)

        return self.read(res_id=res_id)

    def update(self, res_id=None, attributes={}):
        return self.create(res_id=res_id, attributes=attributes)

    def delete(self, res_id=None, attributes={}):
        self.check_mandatory(res_id)
        monitor = attributes.get('monitor')
        state = {'present': False}
        self.save_state(res_id, state, monitor=monitor)

        previous_state = self.read(res_id=res_id)
        self.module.delete_folder(res_id)

        if not self.module.exists(res_id):
            previous_state['present'] = False
            self.response = previous_state

        return self.read(res_id)

    def is_compliant(self, persisted_state, current_state):
        compliant = True

        # First, compare the present flag. If it differs, no need to go
        # further, there's a compliance issue.
        # Check the next path state
        if persisted_state.get("present") != current_state.get("present"):
            compliant = False
            return compliant

        # Secondly, compare path attributes
        for attr in ("name", "owner", "group", "mode"):
            if persisted_state.get(attr) != current_state.get(attr):
                compliant = False
                break

        return compliant

    def _get_owner(self, path, attributes):
        # Default, get the current user. getpass is portable Unix/Windows
        owner = getpass.getuser()

        # If path exists, get path owner
        if self.module.exists(path):
            owner = self.module.owner(path)
        # Overwrite if owner name is provided
        if attributes.get('owner'):
            owner = attributes['owner']

        return owner

    def _get_group(self, path, attributes):
        # Default, get the current user's group.
        # getpass is portable Unix/Windows
        group = getpass.getuser()

        # If path exists, get path group
        if self.module.exists(path):
            group = self.module.group(path)
        # Overwrite if group name is provided
        if attributes.get('group'):
            group = attributes['group']

        return group

    def _get_mode(self, path, attributes):
        # Default, get default mode according to current umask
        mode = self.module.get_default_mode(path)

        # If path exists, get current mode
        if self.module.exists(path):
            mode = self.module.mode(path)

        # If mode is provided, return its octal value as string
        if attributes.get('mode'):
            try:
                mode = oct(int(attributes['mode'], 8))
            except ValueError as err:
                raise ResourceException("Error with path mode (%s)" % err)

        return mode
