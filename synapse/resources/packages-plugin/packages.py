from synapse.resources.resources import ResourcesController
from synapse.synapse_exceptions import ResourceException

from synapse.logger import logger


@logger
class PackagesController(ResourcesController):

    __resource__ = "packages"

    def read(self, res_id=None, attributes=None):
        '''
        Gets the status of a packages.

        Incoming request example:

        {
            "action": "read",
            "id": "httpd",
            "collection": "packages"
        }

        Response:

        {
            "status": {
                "res_id": "httpd",
                "installed": true
            },
            "uuid": "vm1",
            "error": ""
        }
        '''
        status = {}
        try:
            if res_id:
                status['installed'] = self.module.is_installed(res_id)
            else:
                self.logger.info('Retrieving all packages')
                status['installed_packages'] = \
                        self.module.get_installed_packages()

            return self.set_response(status)

        except ResourceException, err:
            return self.set_response('Package Error', error='{0}'.format(err))

    def create(self, res_id=None, attributes={}):
        '''
        Installs a package.

        Incoming request example:

        {
            "action": "create",
            "id": "htop",
            "collection": "packages"
        }

        Response:

        {
            "status": {
                "res_id": "htop",
                "installed": true
            },
            "uuid": "vm1",
            "error": ""
        }
        '''
        status = {}
        response = {}

        try:
            if res_id is None:
                raise ResourceException('Please provide ID')

            installed = self.module.is_installed(res_id)

            if not installed:
                self.logger.info("Installing the package: %s" % res_id)
                self.module.install(res_id)
                self.logger.info('Package {0} '
                                 'has been installed'.format(res_id))
            else:
                self.logger.info('Package {0} '
                                 'is already installed'.format(res_id))

            status['installed'] = self.module.is_installed(res_id)
            response = self.set_response(status)

            monitor = attributes.get('monitor')
            if monitor:
                item = {}
                item['installed'] = True
                self.persister.persist(self.set_response(item))
            elif monitor is False:
                self.persister.unpersist(self.set_response({}))

        except ResourceException, err:
            response = self.set_response('Package Error', error='%s' % err)

        if 'error' in response:
            self.logger.info('Error when installing %s: %s'
                    % (res_id, response['error']))
        return response

    def update(self, res_id=None, attributes=None):
        status = {}
        try:
            if res_id:
                self.logger.info("Updating the package: %s" % res_id)
                self.module.update(res_id)
                status['installed'] = self.module.is_installed(res_id)
            else:
                self.logger.info("Updating the system")
                self.module.update('')

            response = self.set_response(status)

        except ResourceException, err:
            response = self.set_response('Package Error', error='%s' % err)

        if 'error' in response:
            self.logger.info('Error when updating %s: %s'
                    % (res_id, response['error']))

        return response

    def delete(self, res_id=None, attributes=None):
        status = {}
        response = {}
        try:
            if not res_id:
                raise ResourceException('Please provide a resource ID.')

            installed = self.module.is_installed(res_id)
            self.logger.info("Removing the package: %s" % res_id)
            if installed:
                self.module.remove(res_id)
                self.logger.info("Package %s has been removed" % res_id)
            else:
                self.logger.info("Package %s was not installed" % res_id)

            status['installed'] = self.module.is_installed(res_id)
            response = self.set_response(status)

            monitor = attributes.get('monitor')
            if monitor:
                item = {}
                item['installed'] = False
                self.persister.persist(self.set_response(item))
            elif monitor is False:
                self.persister.unpersist(self.set_response({}))

        except ResourceException, err:
            response = self.set_response('Package Error', error='%s' % err)

        if 'error' in response:
            self.logger.info('Error when deleting %s: %s'
                    % (res_id, response['error']))

        return response

    def monitor(self):
        """Monitors packages"""

        try:
            res = getattr(self.persister, "packages")
        except AttributeError:
            return

        response = {}
        for state in res:
            res_id = state["resource_id"]
            with self._lock:
                response = self.read(res_id=res_id)
                if not response["status"] == state["status"]:
                    self._publish(res_id, state, response)
