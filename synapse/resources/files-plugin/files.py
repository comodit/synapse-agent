import base64
import getpass
import urllib2
from datetime import datetime
from urllib2 import URLError

from synapse.resources.resources import ResourcesController
from synapse.logger import logger
from synapse.synapse_exceptions import ResourceException


@logger
class FilesController(ResourcesController):

    __resource__ = "files"

    def read(self, res_id=None, attributes={}):
        self.check_mandatory(res_id)

        present = self.module.is_file(res_id)
        self.status['name'] = res_id
        self.status['present'] = present
        if present:
            if attributes.get('get_content'):
                content = self.module.get_content(res_id)
                self.status['content'] = content
            if attributes.get('md5'):
                md5 = self.module.md5(res_id)
                self.status['md5'] = md5
            self.status['owner'] = self.module.owner(res_id)
            self.status['group'] = self.module.group(res_id)
            self.status['mode'] = self.module.mode(res_id)
            self.status['mod_time'] = self.module.mod_time(res_id)
            self.status['c_time'] = self.module.c_time(res_id)

        return self.status

    def create(self, res_id=None, attributes={}):
        '''
        This method is used to create or update a file on disk.
        ID is mandatory.
        Owner, group and mode are optional. 
        If not specified and file exists, get mode of file on system
        If not specified and file doesn't exist, owner is the current user,
        group is the current group and mode depends on system's umask.
        '''
        self.check_mandatory(res_id)

        owner = self._get_owner(res_id, attributes)
        group = self._get_group(res_id, attributes)
        mode = self._get_mode(res_id, attributes)
        content = self._get_content(attributes)

        self.comply(name=res_id,
                    owner=owner,
                    group=group,
                    mode=mode,
                    mod_time = str(datetime.now()),
                    c_time = str(datetime.now()),
                    present=True,
                    md5=self.module.md5_str(content),
                    monitor=attributes.get('monitor'))

        if not self.module.exists(res_id):
            self.module.create_file(res_id)

        # Update meta of given file
        self.module.update_meta(res_id, owner, group, mode)

        # Set the content in file only if it's a file
        self.module.set_content(res_id, content)

        return self.read(res_id=res_id, attributes=attributes)

    def update(self, res_id=None, attributes={}):
        '''See create method'''

        return self.create(res_id=res_id, attributes=attributes)

    def delete(self, res_id=None, attributes={}):

        self.check_mandatory(res_id)
        self.comply(monitor=False)

        previous_state = self.read(res_id=res_id)
        self.module.delete(res_id)

        if not self.module.exists(res_id):
            previous_state['present'] = False
            self.response = previous_state

        return self.response

    def monitor(self, persisted_state, current_state):
        compliant = True

        # First, compare the present flag. If it differs, no need to go
        # further, there's a compliance issue.
        # Check the next file state
        if persisted_state.get('present') != current_state.get('present'):
            compliant = False
            return compliant

        # Secondly, compare files attributes
        for attr in ('name', 'owner', 'group'):
            if persisted_state.get(attr) != current_state.get(attr):
                compliant = False
                break

        # Fix the retrocompatibility for mode when it used to be only 3 octal
        # digits
        current_mode = current_state.get('mode', '')
        persisted_mode = persisted_state.get('mode', '')
        if len(persisted_mode) == 3:
            if current_mode[-3:] != persisted_mode[-3:]:
                compliant = False
        elif current_mode != persisted_mode:
                compliant = False

        # Then compare modification times. If different, check md5sum
        if persisted_state.get('mod_time') != current_state.get('mod_time'):
            current_state_md5 = self.module.md5(persisted_state['name'])
            if current_state_md5 != persisted_state.get('md5'):
                compliant = False

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

    def _get_content(self, attributes):
        content = attributes.get('content')
        content_by_url = attributes.get('content_by_url')
        encoding = attributes.get('encoding')

        # If content is url provided, overwrite content
        if content_by_url:
            try:
                fd = urllib2.urlopen(content_by_url)
                content = fd.read()
            except URLError, err:
                raise ResourceException("Error: %s (%s)" %
                        (err, content_by_url))

        # Decode if content is base64 encoded.
        if encoding == 'base64':
            try:
                content = base64.b64decode(content)
            except TypeError, err:
                raise ResourceException("Can't b64decode: %s" % err)

        return content
