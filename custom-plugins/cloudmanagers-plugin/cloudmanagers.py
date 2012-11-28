from synapse.resources.resources import ResourcesController
from synapse.resources.resources import ResourceException
from synapse.config import config

from synapse.logger import logger

import cm_util
import cm_openstack

@logger
class CloudmanagersController(ResourcesController):

    __resource__ = "cloudmanagers"
    
    # The types of cloud managers handled by the plugin
    CM_TYPE_OPENSTACK = "openstack"
    CM_TYPE_CLOUDSTACK = "cloudstack"
    CM_TYPE_OPENNEBULA = "opennebula"
    CM_TYPE_OTHER = "other"
    
    # A dict to map the submodules to the cloud managers types
    CM_MAPPING = {cm_openstack: [CM_TYPE_OPENSTACK, CM_TYPE_CLOUDSTACK, CM_TYPE_OPENNEBULA], cm_openstack: [CM_TYPE_OTHER]}
                   
    # The configuration file of the cloud managers plugin
    CLOUDMANAGERS_CONFIG_FILE = config.paths['config_path'] + "/plugins/cloudmanagers.conf"
    
    def __init__(self, mod):
		super(CloudmanagersController, self).__init__(mod)
		self.logger.info("fonction init")
		try:
			pass
		except ResourceException:
			self.logger.warn('{0} in not valid. The {1} plugin will probably not work'.format(self.CLOUDMANAGERS_CONFIG_FILE,self.__resource__))
		
    
    def _get_cloudmanager_type(self, res_id):
		self.logger.info("fonction _get_cloudmanager_type")
		return cm_util.get_config_option(res_id, "cm_type", self.CLOUDMANAGERS_CONFIG_FILE)
        
    def _load_driver_module(self, cm_type):
		for module in self.CM_MAPPING:
			if cm_type in CM_MAPPING[module]:
				try:
					return module
				except ImportError:
					pass
		return None
			

    def read(self, res_id=None, attributes=None):
		self.logger.info("fonction read")
		status = {}
		error = None
		try:
			# If the cloud manager's id is not specified, the method will return a
			# list of the managed cloud managers ids
			if res_id == "":
				status['cloudmanagers'] = self._get_cloudmanagers()
				
			# If only the cloud manager's id is given, the method will return a
			# list of the existing virtual machines on the cloud manager
			elif (attributes is None or "name" not in attributes):
				status['cloudmanagers'] = res_id
				status['url'] = cm_util.get_config_option(res_id, "url", self.CLOUDMANAGERS_CONFIG_FILE)
				
				# Retrieve the good module
				cm_type = self._get_cloudmanager_type(res_id)
				module = self._load_driver_module(cm_type)
				
				# Retrieve the list of VMs
				status['VMs'] = module._get_VMs()
			else:
				pass
		except ResourceException, ex:
			error = self._append_error(error, ex)
		except Exception, ex:
			error = self._append_error(error, "Unknown error : %s" % ex)
		response = self.set_response(status, error=error)
		return response


    def create(self, res_id=None, attributes={}):
        pass

    def update(self, res_id=None, attributes=None):
        pass

    def delete(self, res_id=None, attributes=None):
        pass
        

#-----------------------------------------------------------------------------

    def _append_error(self, error, string):
        '''
        Appends an error string to a list.

        @param error: the list of error messages
        @type error: list

        @param string: the string to append to the list
        @type string: str
        '''
        if error is None:
            error = []

        error.append('%s' % string)

        return error

#-----------------------------------------------------------------------------

    def _get_cloudmanagers(self):
        '''
        Returns cloudmanagers from the config file
        '''
        config = cm_util.read_config_file(self.CLOUDMANAGERS_CONFIG_FILE)
        import pdb; pdb.set_trace()
        # Get a list of sections corresponding to cloud managers ids
        cloudmanagers = config.sections()
        try:
            # Remove general section
            cloudmanagers.remove("general")
        except ValueError:
            pass

        return cloudmanagers
#-----------------------------------------------------------------------------
