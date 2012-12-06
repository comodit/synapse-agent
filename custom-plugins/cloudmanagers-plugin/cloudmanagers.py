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
                
                # Initialize mandatory attributes depending on cloud manager's type
                module._init_cloudmanager_attributes(res_id, attributes)
                
				# Retrieve the list of VMs
				status['VMs'] = module._get_VMs(attributes)
			else:
				# Retrieve the good module
				cm_type = self._get_cloudmanager_type(res_id)
				module = self._load_driver_module(hyp_type)
				
				# Check if the VM exists and retrieve the various important fields to return
				if module._exists(attributes):
					status['cloudmanager'] = res_id
					status['url'] = cm_util.get_config_option(res_id, "url", self.CLOUDMANAGERS_CONFIG_FILE)
					status['vm_name'] = attributes['name']
					
					try:
						status['vm_vcpus'] = module._get_vcpus(attributes)
					except ResourceException, ex:
						status['vm_vcpus'] = str(ex)
						
					status['vm_vnc_port'] = module._get_vnc_port(attributes)
					
					# Verifies if this is a vnx request
					# TODO: the vnc part should come here
					
				else:
					error = self._append_error(error, "The specified VM doesn't exist")
					
				num_status = module._get_status(attributes)
				status['vm_status'] = module._get_readable_status(num_status)
					
		except ResourceException, ex:
			error = self._append_error(error, ex)
		except Exception, ex:
			error = self._append_error(error, "Unknown error : %s" % ex)
		response = self.set_response(status, error=error)
		return response
#-----------------------------------------------------------------------------

    def create(self, res_id=None, attributes={}):
        status = {}
        error = None

        passed = True

        cm_type = None
        module = None
        
        try:
            # Check mandatory attributes
            required_keys = ["name"]
            self._check_keys_in_dict(attributes, required_keys)
            
            # Check integer attributes
            int_attributes_keys = ["flavor", "vnc_port"]
            self._check_int_attributes(attributes, int_attributes_keys)
            
            # Check attributes values
            self._check_attributes_values(attributes)
            
            # Retrieve the good module
            cm_type = self._get_cloudmanager_type(res_id)
            module = self._load_driver_module(cm_type)
            
            # Initialize mandatory attributes depending on cloud manager's type
            module._init_cloudmanager_attributes(res_id, attributes)
            
        except ResourceException, ex:
            passed = False
            error = self._append_error(error, ex)
        except Exception, ex:
            error = self._append_error(error, "Unknown error : %s" % ex)
            
        # Check if the virtual machine exists
        if passed and not module._exists(attributes):
            
            try:
                # Initialize mandatory attributes depending on cloudmanager's type
                module._init_cloudmanager_attributes(res_id, attributes)
                cm_type = self._get_cloudmanager_type(res_id)
                # Initialize the virtual machine dictionary
                dict_vm = {'type': cm_type,
                    'name': attributes['name'],
                    'memory': int(attributes['memory']),
                    'num_cpu': int(attributes.get('num_cpu', 1)),
                    'arch_type': attributes.get('arch_type', "i686"),
                    'os_type': attributes['os_type'],
                    'kernel_path': attributes['kernel_path'],
                    'initrd_path': attributes['initrd_path'],
                    'cmd_line': attributes.get('cmd_line', ""),
                    'boot_dev': attributes.get('boot_dev', "hd"),
                    'emulator_path': attributes.get('emulator_path', ""),
                    'disk_driver': attributes.get('disk_driver', "qemu"),
                    'disk_type': attributes.get('disk_type', "raw"),
                    'bridged': attributes.get('bridged', False),
                    'mac_address':
                        attributes.get('mac_address',
                                       self._generate_mac_address(
                                           self.MAC_PREFIX)),
                    'bridge_interface': attributes.get('bridge_interface',
                                                       ""),
                    'vnc_port': int(attributes.get('vnc_port', -1)),
                    'floppy': attributes.get('floppy', False),
                    'floppy_path': attributes.get('floppy_path', ""),
                    'cdrom': attributes.get('cdrom', False),
                    'cdrom_path': attributes.get('cdrom_path', ""),
                    'flavor': attributes.get('flavor', ""),
                    'image': attributes.get('image', ""),
                    'key': attributes.get('key', "")
                }
                
                self.logger.debug("VM details: %s" % dict_vm)
                
                # Create and provision the VM
                state = module._create_VM(res_id, attributes, dict_vm)
                
                status['vm_status'] = module._get_readable_status(state)
                status['created'] = True
                status['vm_name'] = attributes['name']

            # If there was an error during the virtual machine's creation
            except ResourceException, ex:
                status['vm_name'] = attributes['name']
                status['vm_status'] = cm_util.VM_STATE_UNKNOWN
                status['created'] = False
                error = self._append_error(error, ex)

            except Exception, ex:
                error = self._append_error(error, "Unknown error : %s" % ex)
                traceback.print_exc(file=sys.stdout)
        # If a virtual machine with the same name already exists
        elif passed:
            status['vm_name'] = attributes['name']
            state = module._get_status(attributes)
            status['vm_status'] = module._get_readable_status(state)
            status['created'] = False
            error = self._append_error(error, "A VM already exists under this name")
            
        status['cloudmanager'] = res_id
        
        response = self.set_response(status, error=error)
        
        return response
#-----------------------------------------------------------------------------
    def update(self, res_id=None, attributes=None):
        pass
#-----------------------------------------------------------------------------
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
