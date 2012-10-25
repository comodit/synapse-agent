import getpass
from datetime import datetime

from synapse.resources.resources import ResourcesController
from synapse.logger import logger
from synapse.synapse_exceptions import ResourceException


@logger
class DirectoriesController(ResourcesController):

    __resource__ = "directories"

    def read(self, res_id=None, attributes={}):
        self.check_mandatory(res_id)

        present = self.module.is_dir(res_id)
        self.status['present'] = present
        if present:
            self.status['owner'] = self.module.owner(res_id)
            self.status['group'] = self.module.group(res_id)
            self.status['mode'] = self.module.mode(res_id)
            self.status['mod_time'] = self.module.mod_time(res_id)
            self.status['c_time'] = self.module.c_time(res_id)

        return self.status

    def create(self, res_id=None, attributes={}):
        self.check_mandatory(res_id)

        owner = self._get_owner(res_id, attributes)
        group = self._get_group(res_id, attributes)
        mode = self._get_mode(res_id, attributes)

        self.comply(owner=owner,
                    group=group,
                    mode=mode,
                    mod_time = str(datetime.now()),
                    c_time = str(datetime.now()),
                    present=True,
                    monitor=attributes.get('monitor'))

        self.module.create_folders(res_id)

        # Update meta of given file
        self.module.update_meta(res_id, owner, group, mode)

        return self.read(res_id=res_id)

    def update(self, res_id=None, attributes={}):
        return self.create(res_id=res_id, attributes=attributes)

    def delete(self, res_id=None, attributes={}):
        self.check_mandatory(res_id)
        self.comply(monitor=False)

        previous_state = self.read(res_id=res_id)
        self.module.delete_folder(res_id)

        if not self.module.exists(res_id):
            previous_state['present'] = False
            self.response = previous_state

        return self.response

    def monitor(self):
        # Get the list of persisted files states.
        try:
            res = getattr(self.persister, "directories")
        except AttributeError:
            return

        # For every file state
        for state in res:
            # Get the file path and its current state on the system
            res_id = state["resource_id"]
            with self._lock:
                try:
                    self.response = self.read(res_id=res_id)
                except ResourceException as err:
                    self.logger.error(err)

            wanted = state["status"]
            current = self.response
            change_detected = False

            # First, compare the present flag. If it differs, no need to go
            # further, there's a compliance issue.
            # Check the next file state
            if wanted.get("present") != current.get("present"):
                self._publish(res_id, state, self.response)
                continue

            # Secondly, compare files attributes
            for attr in ("name", "owner", "group", "mode"):
                if wanted.get(attr) != current.get(attr):
                    change_detected = True
                    break

            # Publish if somethings detected
            if change_detected:
                self._publish(res_id, state, self.response)

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
