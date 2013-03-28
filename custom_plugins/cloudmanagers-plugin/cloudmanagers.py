from synapse.resources.resources import ResourcesController
from synapse.resources.resources import ResourceException
from synapse.config import config

from synapse.logger import logger
import traceback
import sys
import os
import uuid
import random
import cm_util
import cm_openstack

@logger
class CloudmanagersController(ResourcesController):

    __resource__ = "cloudmanagers"

    # The types of cloud managers handled by the plugin
    CM_TYPE_OPENSTACK = "openstack"

    # A dict to map the submodules to the cloud managers types
    CM_MAPPING = {cm_openstack: [CM_TYPE_OPENSTACK]}

    # The configuration file of the cloud managers plugin
    CLOUDMANAGERS_CONFIG_FILE = config.paths['config_path'] + "/plugins/cloudmanagers.conf"

#-----------------------------------------------------------------------------

    def __init__(self, mod):
		super(CloudmanagersController, self).__init__(mod)
		try:
			pass
		except ResourceException:
			self.logger.warn('{0} in not valid. The {1} plugin will probably not work'.format(self.CLOUDMANAGERS_CONFIG_FILE,self.__resource__))

#-----------------------------------------------------------------------------

    def _get_cloudmanager_type(self, res_id):
		return cm_util.get_config_option(res_id, "cm_type", self.CLOUDMANAGERS_CONFIG_FILE)

#-----------------------------------------------------------------------------

    def _load_driver_module(self, cm_type):
        for module in self.CM_MAPPING:
            if cm_type in self.CM_MAPPING[module]:
                try:
                    return module
                except ImportError:
                    pass
        return None

#-----------------------------------------------------------------------------

    def listimages(self, res_id=None, attributes=None):
        status={}
        error = None
        if(attributes is None):
            status['cloudmanagers'] = res_id
            status['url'] = cm_util.get_config_option(res_id, "url", self.CLOUDMANAGERS_CONFIG_FILE)

            # Retrieve the good module
            cm_type = self._get_cloudmanager_type(res_id)
            module = self._load_driver_module(cm_type)

            # Initialize mandatory attributes depending on cloud manager's type
            module._init_cloudmanager_attributes(res_id, attributes)

            status['images'] = module._get_images(attributes)

        else:
            raise ResourceException("No arguments are yet allowed for this method")

        return status

#-----------------------------------------------------------------------------

    def read(self, res_id=None, attributes=None):
        status = {}
        error = None
        # If the cloud manager's id is not specified, the method will return a
        # list of the managed cloud managers ids
        if res_id == "":
            status['cloudmanagers'] = self._get_cloudmanagers()

        # If only the cloud manager's id is given, the method will return a
        # list of the existing virtual machines on the cloud manager
        elif (attributes is None or "name" not in attributes and "listimages" not in attributes):
            status['cloudmanagers'] = res_id
            status['url'] = cm_util.get_config_option(res_id, "url", self.CLOUDMANAGERS_CONFIG_FILE)

            # Retrieve the good module
            cm_type = self._get_cloudmanager_type(res_id)
            module = self._load_driver_module(cm_type)

            # Initialize mandatory attributes depending on cloud manager's type
            module._init_cloudmanager_attributes(res_id, attributes)

            # Retrieve the list of VMs
            status['VMs'] = module._get_VMs(attributes)

        elif ("listimages" in attributes):
            status['cloudmanagers'] = res_id
            status['url'] = cm_util.get_config_option(res_id, "url", self.CLOUDMANAGERS_CONFIG_FILE)

            # Retrieve the good module
            cm_type = self._get_cloudmanager_type(res_id)
            module = self._load_driver_module(cm_type)

            # Initialize mandatory attributes depending on cloud manager's type
            module._init_cloudmanager_attributes(res_id, attributes)

            status['images'] = module._get_images(attributes)
        else:
            # Retrieve the good module
            cm_type = self._get_cloudmanager_type(res_id)
            module = self._load_driver_module(cm_type)
            # Initialize mandatory attributes depending on cloud manager's type
            module._init_cloudmanager_attributes(res_id, attributes)

            # Check if the VM exists and retrieve the various important fields to return
            if module._exists(attributes):
                status['cloudmanager'] = res_id
                status['url'] = cm_util.get_config_option(res_id, "url", self.CLOUDMANAGERS_CONFIG_FILE)
                status['vm_name'] = attributes['name']

                try:
                    status['vm_vcpus'] = module._get_vcpus(attributes)
                except ResourceException, ex:
                    status['vm_vcpus'] = str(ex)

                try:
                    vm = module._get_VM(attributes)
                    vm_id = vm['id']
                    flavor = module._get_flavor(attributes, vm['id'])
                    status['vm_flavor'] = flavor['id']
                except ResourceException, ex:
                    status['vm_flavor'] = str(ex)

                status['vm_vnc_port'] = module._get_vnc_port(attributes)

                # Verifies if this is a vnx request
                # TODO: the vnc part should come here

            else:
                raise ResourceException("The specified VM doesn't exist")

            num_status = module._get_status(attributes)
            status['vm_status'] = module._get_readable_status(num_status)

        return status
#-----------------------------------------------------------------------------

    def create(self, res_id=None, attributes={}):
        status = {}
        error = ''

        passed = True

        cm_type = None
        module = None

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


        # Check if the virtual machine exists
        if passed and not module._exists(attributes):

            try:
                # Initialize mandatory attributes depending on cloudmanager's type
                module._init_cloudmanager_attributes(res_id, attributes)
                cm_type = self._get_cloudmanager_type(res_id)
                # Initialize the virtual machine dictionary
                dict_vm = {'type': cm_type,
                    'name': attributes['name'],
                    'flavor': attributes.get('flavor', ""),
                    'image': attributes.get('image', ""),
                    'key': attributes.get('key', ""),
                    'user-data': attributes.get('user-data', "")
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

            except Exception, ex:
                traceback.print_exc(file=sys.stdout)
        # If a virtual machine with the same name already exists
        elif passed:
            status['vm_name'] = attributes['name']
            state = module._get_status(attributes)
            status['vm_status'] = module._get_readable_status(state)
            status['created'] = False
            raise ResourceException("A VM already exists under this name")

        status['cloudmanager'] = res_id
        return status
#-----------------------------------------------------------------------------
    def update(self, res_id=None, attributes={}):
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

        # Retrieve the good module and the corresponding connection
        cm_type = self._get_cloudmanager_type(res_id)
        module = self._load_driver_module(cm_type)

        # Initialize mandatory attributes depending on cloud manager's type
        module._init_cloudmanager_attributes(res_id, attributes)

        # If none of the tests has passed, an error message is appended
        if cpt == 0:
            raise ResourceException("There must be at least "
                                       "one command to do an update")

        # If the virtual machine exists
        elif module._exists(attributes):
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
                    new_flavor = attributes["flavor"]

                    flavor_dict = module._set_flavor(attributes, vm_id, current_flavor["id"], new_flavor)
                    status['vm_flavor'] = flavor_dict["id"]


        # If the virtual machine doesn't exist
        else:
            raise ResourceException("The specified VM doesn't "
                                       "exist")

        status['cloudmanager'] = res_id

        return status

#-----------------------------------------------------------------------------
    def delete(self, res_id=None, attributes=None):
        status = {}
        error = None

        required_keys = ["name"]

        # Check if the name of the virtual machine to delete exists in the
        # attributes
        self._check_keys_in_dict(attributes, required_keys)

        # Retrieve the good module
        cm_type = self._get_cloudmanager_type(res_id)
        module = self._load_driver_module(cm_type)

        # Initialize mandatory attributes depending on cloud manager's type
        module._init_cloudmanager_attributes(res_id, attributes)

        # Check if the virtual machine exists
        if module._exists(attributes):
            status['vm_name'] = attributes['name']

            num_status = module._get_status(attributes)

            # If the machine is running and the attribute 'force' is not
            #specified, then the machine can't be removed
            if (("force" not in attributes or attributes['force'] == False)
                and module._get_readable_status(num_status) == cm_util.VM_STATE_RUNNING):
                    status['vm_status'] = module._get_readable_status(num_status)
                    status['deleted'] = False
                    raise ResourceException("The VM is "
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
            raise ResourceException("The specified VM doesn't exist")

        status['cloudmanager'] = res_id
        return status


#-----------------------------------------------------------------------------

    def _get_cloudmanagers(self):
        '''
        Returns cloudmanagers from the config file
        '''
        config = cm_util.read_config_file(self.CLOUDMANAGERS_CONFIG_FILE)
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

    def _check_int_attributes(self, attributes, keys):
        '''
        Checks integer values in a dictionary

        @param attributes: the dictionary on which the integer keys will be
                            checked
        @type attributes: dict

        @param keys: the keys of the integer attributes
        @type keys: list
        '''
        for key in keys:
            if key in attributes:
                try:
                    int(attributes[key])
                except ValueError:
                    raise ResourceException("Attribute '%s' must be integer" %
                                            key)
                except TypeError:
                    raise ResourceException("Attribute '%s' is None" % key)

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
                cm_util.VM_STATE_REBOOTING: module._reboot,
                cm_util.VM_STATE_RESUME: module._resume
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
