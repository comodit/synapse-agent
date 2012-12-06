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
        status = {}
        error = None
        
        keys_upd_status = ["status"]
        keys_upd_flavor = ["flavor"]
        
        cmd_mandatory_keys = [keys_upd_status, keys_upd_flavor]
        
        # Check if there is at least one update command with all required
        # attributes
        cpt = 0
        for keys in cmd_mandatory_keys:
            try:
                self._check_keys_in_dict(attributes, keys)
                cpt += 1
            except ResourceException:
                pass
                
        try:
            # Retrieve the good module and the corresponding connection
            cm_type = self._get_cloudmanager_type(res_id)
            module = self._load_driver_module(cm_type)

            # If none of the tests has passed, an error message is appended
            if cpt == 0:
                error = self._append_error(error, "There must be at least "
                                           "one command to do an update")

            # If the virtual machine exists
            elif module._exists(attributes):
                try:
                    # Check the semantic values of some attributes
                    self._check_attributes_values(attributes)

                    status['vm_name'] = attributes['name']

                    # Update the status
                    if "status" in attributes:
                        num_status = module._get_status(attributes)
                        str_status = module._get_readable_status(num_status)

                        # Check if the virtual machine is not in the required
                        # state
                        if (attributes['status'] != str_status):
                                num_status = self._set_status(res_id, attributes)
                                status['vm_status'] = module._get_readable_status(num_status)
                        else:
                            status['vm_status'] = str_status
                            
                    # Update the flavor
                    if ("flavor" in attributes):

                            vm = module._get_VM(attributes)
                            vm_id = vm['id']
                            current_flavor = module._get_flavor(attributes, vm_id)
                            
                            # Check if the current flavor is not equal to the required one
                            if current_size != new_size:
                                status['vm_flavor'] = module._set_flavor(attributes, vm_id, flavor)
                            else:
                                status['vm_flavor'] = module._get_flavor(attributes, vm_id)
                                
                # If there was an error during the update operations
                except ResourceException, ex:
                    state = module._get_status(attributes)
                    status['vm_state'] = module._get_readable_status(state)
                    error = self._append_error(error, ex)

            # If the virtual machine doesn't exist
            else:
                status['vm_state'] = cm_util.VM_STATE_UNKNOWN
                error = self._append_error(error, "The specified VM doesn't "
                                           "exist")
        except ResourceException, ex:
            error = self._append_error(error, ex)
        except Exception, ex:
            error = self._append_error(error, "Unknown error : %s" % ex)

        status['cloudmanager'] = res_id

        response = self.set_response(status, error=error)

        return response
        
#-----------------------------------------------------------------------------
    def delete(self, res_id=None, attributes=None):
        status = {}
        error = None

        required_keys = ["name"]

        try:
            # Check if the name of the virtual machine to delete exists in the
            # attributes
            self._check_keys_in_dict(attributes, required_keys)

            # Retrieve the good module
            cm_type = self._get_cloudmanager_type(res_id)
            module = self._load_driver_module(cm_type)
            
            # Check if the virtual machine exists
            if module._exists(connection, attributes):
                status['vm_name'] = attributes['name']

                num_status = module._get_status(attributes)

                # If the machine is running and the attribute 'force' is not
                #specified, then the machine can't be removed
                if (("force" not in attributes or attributes['force'] == False)
                    and module._get_readable_status(num_status) == cm_util.VM_STATE_RUNNING):
                        status['vm_status'] = module._get_readable_status(num_status)
                        status['deleted'] = False
                        error = self._append_error(error, "The VM is "
                                    "currently running. Use the option "
                                    "force or shutdown the VM.")

                # Otherwise, we can remove the virtual machine
                else:
                    state = module._delete_VM(attributes)
                    status['vm_status'] = module._get_readable_status(state)
                    status['deleted'] = True

            # If the machine doesn't exist
            else:
                status['vm_name'] = attributes['name']
                status['vm_status'] = cm_util.VM_STATE_UNKNOWN
                status['deleted'] = False
                error = self._append_error(error,
                            "The specified VM doesn't exist")

        except ResourceException, ex:
            error = self._append_error(error, ex)
        except Exception, ex:
            error = self._append_error(error, "Unknown error : %s" % ex)

        status['cloudmanager'] = res_id

        response = self.set_response(status, error=error)

        return response

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

    def _check_keys_in_dict(self, dictionary, keys):
        '''
        Checks if keys exist in a dict.

        @param dictionary: the dictionary on which the keys will be checked
        @type dictionary: dict

        @param keys: the keys to check in the given dictionary
        @type keys: list
        '''
        for key in keys:
            if key not in dictionary:
                raise ResourceException("Mandatory attribute '%s' is missing"
                                        % key)
            elif key is None:
                raise ResourceException("Mandatory attribute '%s' is None"
                                        % key)

#-----------------------------------------------------------------------------

    def _check_attributes_values(self, attributes):
        '''
        Checks values of the attributes dictionary in terms of semantic

        @param attributes: the dictionary of attributes
        @type attributes: dict
        '''
        if "name" in attributes:
            if attributes['name'] == "":
                raise ResourceException("The VM name must not be empty.")

        if "flavor" in attributes:
            if attributes['flavor'] == "" :
                raise ResourceException("The flavor must be specified.")

        if "image" in attributes:
            if attributes['image'] == "":
                raise ResourceException("The image must be specified")

#-----------------------------------------------------------------------------

    def _set_status(self, res_id, attributes):
        '''
        Retrieves the status number and executes the corresponding action.

        @param res_id: cloud manager's id
        @type res_id: str

        @param attributes: the different attributes which will be used to
                            update the status of a virtual machine
        @type attributes: dict
        '''
        # Retrieve the good module
        cm_type = self._get_cloudmanager_type(res_id)
        module = self._load_driver_module(cm_type)

        # If the virtual machine is already in the given state, then this state
        # is returned
        if attributes['status'] == module._get_status(attributes):
            return module._get_status(attributes)

        try:
            # Retrieve a reference to the method of the module to call to
            # update the status of a virtual machine
            status_action = {
                cm_util.VM_STATE_RUNNING: self._run_vm(res_id, attributes),
                cm_util.VM_STATE_PAUSED: module._pause,
                cm_util.VM_STATE_SHUTDOWN: module._shutdown,
                cm_util.VM_STATE_SHUTOFF: module._shutoff,
                cm_util.VM_STATE_REBOOTING: module._reboot
            }[attributes['status']]

        except KeyError:
            raise ResourceException("The given status is unknown")

        # Call the method and return the final status of the virtual machine
        return status_action(attributes)

#-----------------------------------------------------------------------------

    def _run_vm(self, res_id, attributes):
        '''
        Returns the most appropriate method to run the VM

        @param res_id: cloud manager's id
        @type res_id: str

        @param attributes: the different attributes which will be used to
                            run a virtual machine
        @type attributes: dict
        '''
        # Retrieve the good module
        cm_type = self._get_cloudmanager_type(res_id)
        module = self._load_driver_module(cm_type)

        # Retrieve the statusd of the virtual machine
        status = module._get_status(attributes)

        # Resume the virtual machine if it's paused and start it in other cases
        if module._get_readable_status(status) == cm_util.VM_STATE_PAUSED:
            return module._resume
        else:
            return module._start
