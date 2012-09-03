import base64
import urllib2
import os
from datetime import datetime
from urllib2 import URLError

from synapse.resources.resources import ResourcesController
from synapse.logger import logger
from synapse.synapse_exceptions import ResourceException


@logger
class FilesController(ResourcesController):

    __resource__ = "files"

    def read(self, res_id=None, attributes=None):
        '''This method gets the status and content of a file. Whether it's
        present or not as a file on disk or as a resource.
        '''

        status = {}
        try:
            # Id is mandatory.
            if not res_id:
                raise ResourceException('Please provide an ID')
            if os.path.isdir(res_id):
                status['filelist'] = self.module.list_dir(res_id)
            status['name'] = res_id
            status['owner'] = self.module.owner(res_id)
            status['group'] = self.module.group(res_id)
            status['mode'] = self.module.mode(res_id)
            status['mod_time'] = self.module.mod_time(res_id)
            status['c_time'] = self.module.c_time(res_id)
            status['present'] = True

            if attributes:
                if attributes.get('get_content'):
                    content = self.module.get_content(res_id)
                    status['content'] = content
                if attributes.get('md5'):
                    md5 = self.module.md5(res_id)
                    status['md5'] = md5

            response = self.set_response(status)

        except ResourceException, err:
            status = dict(present=False)
            response = self.set_response(status, error='{0}'.format(err))

        if 'error' in response:
            self.logger.info('Error when updating file %s: %s'
                    % (res_id, response['error']))

        return response

    def create(self, res_id=None, attributes={}):
        '''
        This method is used to create or update a file on disk.
        ID is mandatory.
        '''

        self.logger.info('Creating/Updating file [{0}]'.format(res_id))

        #---------------------------------------------------------
        # Meta part
        #---------------------------------------------------------
        # Owner, group and mode will be used as parameters for
        # os.chmod() and os.chown() . If they're not provided, we want
        # them to remain unchanged, thus "-1" as default value.
        owner = attributes.get('owner', -1) or -1
        group = attributes.get('group', -1) or -1
        mode = attributes.get('mode', -1) or -1

        content = attributes.get('content')
        content_by_url = attributes.get('content_by_url')
        encoding = attributes.get('encoding')
        get_content = attributes.get('get_content')

        try:
            # Id is mandatory to create a file.
            if not res_id:
                raise ResourceException('Please provide id.')
            if mode != -1:
                try:
                    mode = oct(int(mode, 8))
                except ValueError:
                    raise ResourceException("Invalid file mode")

            # Try to create the file.
            try:
                self.module.create_file(res_id)

            # If it already exists, continue anyway
            except ResourceException:
                pass

            # Update meta of given file
            self.module.update_meta(res_id, owner, group, mode)

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

            # Set the content in file
            self.module.set_content(res_id, content)

            monitor = attributes.get('monitor')
            if monitor:
                item = {}
                item['name'] = res_id
                item['owner'] = owner
                item['group'] = group
                item['mode'] = mode
                item['mod_time'] = str(datetime.now())
                item['c_time'] = str(datetime.now())
                item['present'] = True
                item['md5'] = self.module.md5_str(content)
                self.persister.persist(self.set_response(item))
            elif monitor is False:
                item = {}
                item['present'] = False
                self.persister.unpersist(self.set_response(item))

            #---------------------------------------------------------
            # Building the response
            #---------------------------------------------------------
            attributes = {}
            attributes['md5'] = True

            if get_content:
                attributes['get_content'] = True

            response = self.read(res_id=res_id, attributes=attributes)

            self.logger.info('File [{0}] successfully updated'.format(res_id))

        except ResourceException, err:
            response = self.set_response('File Error', error='%s' % err)

        if 'error' in response:
            self.logger.info('Error when creating/updating the file %s: %s'
                    % (res_id, response['error']))

        return response

    def update(self, res_id=None, attributes=None):
        '''See create method'''

        return self.create(res_id=res_id, attributes=attributes)

    def delete(self, res_id=None, attributes=None):
        '''
        This method deletes a file on disk. Deleting a file does not mean
        deleting the resource. The resource will still be monitored with
        the flag "present" set to False.
        '''

        response = {}
        self.logger.info('Deleting file [{0}]'.format(res_id))
        try:
            if not res_id:
                raise ResourceException('Please provide file id.')

            monitor = attributes.get('monitor')
            if monitor:
                item = {}
                item['present'] = True
                self.persister.persist(self.set_response(item))
            elif monitor is False:
                item = {}
                self.persister.unpersist(self.set_response(item))

            #-------------------------------------------------------------
            # Delete the file
            #-------------------------------------------------------------
            status = self.read(res_id=res_id)
            self.module.delete(res_id)

            if not self.module.exists(res_id):
                self.logger.info('File [{0}] successfully deleted'.format(
                                                                    res_id))
                status["present"] = False
                response = self.set_response(status)
            else:
                raise ResourceException("Could not delete the file.")

        except ResourceException, err:
            response = self.set_response('File Error', error='%s' % err)

        if 'error' in response:
            self.logger.info('Error when deleting the file %s: %s'
                    % (res_id, response['error']))

        return response

    def monitor(self):
        """Monitors files"""

        # Get the list of persisted files states.
        try:
            res = getattr(self.persister, "files")
        except AttributeError:
            return

        response = {}

        # For every file state
        for state in res:
            # Get the file path and its current state on the system
            res_id = state["resource_id"]
            with self._lock:
                response = self.read(res_id=res_id)

            wanted = state["status"]
            current = response["status"]
            change_detected = False

            # First, compare the present flag. If it differs, no need to go
            # further, there's a compliance issue.
            # Check the next file state
            if wanted.get("present") != current.get("present"):
                self._publish(res_id, state, response)
                continue

            # Secondly, compare files attributes
            for attr in ("name", "owner", "group", "mode"):
                if wanted.get(attr) != current.get(attr):
                    change_detected = True
                    break

            # Then compare modifications times. If different, check md5sum
            if wanted.get("mod_time") != current.get("mod_time"):
                current = response["status"]
                try:
                    with self._lock:
                        current_md5 = self.module.md5(res_id)
                except ResourceException:
                    pass
                if current_md5 != wanted.get("md5"):
                    change_detected = True
                else:
                    # If md5sum don't differ, persist new mod_time.
                    state['status']['mod_time'] = current['mod_time']
                    self.persister.persist(state)

            # Publish if somethings detected
            if change_detected:
                self._publish(res_id, state, response)
