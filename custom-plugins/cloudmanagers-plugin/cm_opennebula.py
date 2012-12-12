import cm_util
from synapse.config import config
from synapse.syncmd import exec_cmd
from synapse.resources.resources import ResourceException
import json
from restful.restful_lib import Connection
import ConfigParser

from synapse.logger import logger
from synapse.syncmd import exec_cmd

# The configuration file of the cloud managers plugin
CLOUDMANAGERS_CONFIG_FILE = config.paths['config_path'] + "/plugins/cloudmanagers.conf"


#-----------------------------------------------------------------------------

def _get_VMs(attributes):
    conn = Connection(attributes["cm_nova_url"], username="", password="")
    tenant_id, x_auth_token = _get_keystone_tokens(attributes)
    resp = conn.request_get("/" + tenant_id +"/servers", args={}, headers={'content-type':'application/json', 'accept':'application/json', 'x-auth-token':x_auth_token})
    status = resp[u'headers']['status']
    if status == '200' or status == '304':
        servers = json.loads(resp['body'])
        i = 0
        vms = []
        for r in servers['servers']:
            vms.append(r['name'])
            i = i+1
        return vms
    else:
        print 'Error status code: ',status
#-----------------------------------------------------------------------------
def _get_VM(attributes):
    conn = Connection(attributes["cm_nova_url"], username="", password="")
    tenant_id, x_auth_token = _get_keystone_tokens(attributes)
    resp = conn.request_get("/" + tenant_id +"/servers/detail", args={}, headers={'content-type':'application/json', 'accept':'application/json', 'x-auth-token':x_auth_token})
    status = resp[u'headers']['status']
    found = 0
    if status == '200' or status == '304':
        servers = json.loads(resp['body'])
        for vm in servers['servers']:
            if attributes['name'] == vm['name']:
                found = 1
                #self.logger.debug("_get_VM(): attributes['name'] vaut %s" % attributes['name'])
                return vm
        if found == 0:
            #return False
            raise ResourceException("vm %s not found" % attributes['name'])
    else:
        print 'Error status code: ',status

#-----------------------------------------------------------------------------

def _exists(attributes):
    try:
        _get_VM(attributes)
        return True
    except ResourceException:
        return False
        
#-----------------------------------------------------------------------------

def _get_vcpus(attributes):
    vm = _get_VM(attributes)

    if not vm['status'] == 'ACTIVE':
        raise ResourceException("The CPUs info can't be retrieved while the VM is not running")
    vm_id = vm['id']
    flavor = _get_flavor(attributes, vm_id)
    return flavor['vcpus']
    
#-----------------------------------------------------------------------------

def _get_flavor(attributes, vm_id):
    conn = Connection(attributes["cm_nova_url"], username="", password="")
    tenant_id, x_auth_token = _get_keystone_tokens(attributes)
    resp = conn.request_get("/" + tenant_id +"/servers/" + vm_id, args={}, headers={'content-type':'application/json', 'accept':'application/json', 'x-auth-token':x_auth_token})
    status = resp[u'headers']['status']
    if status == '200' or status == '304':
        server = json.loads(resp['body'])
        flavor_id = server['server']['flavor']['id']
    else:
        print 'Error status code: ',status
    resp = conn.request_get("/" + tenant_id +"/flavors/" + flavor_id, args={}, headers={'content-type':'application/json', 'accept':'application/json', 'x-auth-token':x_auth_token})
    status = resp[u'headers']['status']
    if status == '200' or status == '304':
        flavor = json.loads(resp['body'])
    else:
        print 'Error status code: ',status
    return flavor['flavor']
    
#-----------------------------------------------------------------------------

def _set_flavor(attributes, vm_id, flavor):
    conn = Connection(attributes["cm_nova_url"], username="", password="")
    tenant_id, x_auth_token = _get_keystone_tokens(attributes)
    body = '{"resize": {"flavorRef":"'+ flavor + '"}}'
    headers = {"Content-type": "application/json", "x-auth-token": x_auth_token.encode()}
    uri = tenant_id + "/servers" + vm_id + "/action"
    resp = conn.request_post(uri, body=body, headers=headers)
    if status == '200' or status == '304':
        data = json.loads(resp['body'])
        print "vm creee et get_status vaut", _get_status(attributes)
        return _get_status(attributes)
    else:
        print 'Error http status code: ',status

#-----------------------------------------------------------------------------

def _get_vnc_port(attributes):
    return '6969'
    
#-----------------------------------------------------------------------------

def _get_status(attributes):
    try:
        vm = _get_VM(attributes)
        return vm['status']
    except (ResourceException, 'No status'):
        return 0

#-----------------------------------------------------------------------------

def _init_cloudmanager_attributes(res_id, attributes):
    cloudmanager_type = cm_util.get_config_option(res_id, 'cm_type', CLOUDMANAGERS_CONFIG_FILE)
	# Initialize here specific attributes for OpenStack
    attributes["cm_base_url"] = cm_util.get_config_option(res_id, "url", CLOUDMANAGERS_CONFIG_FILE)
    attributes["cm_keystone_url"] = cm_util.get_config_option(res_id, "keystone_base_url", CLOUDMANAGERS_CONFIG_FILE)
    attributes["cm_nova_url"] = cm_util.get_config_option(res_id, "nova_base_url", CLOUDMANAGERS_CONFIG_FILE)
    attributes["cm_tenant_name"] = cm_util.get_config_option(res_id, "tenant_name", CLOUDMANAGERS_CONFIG_FILE)
    attributes["cm_username"] = cm_util.get_config_option(res_id, "username", CLOUDMANAGERS_CONFIG_FILE)
    attributes["cm_password"] = cm_util.get_config_option(res_id, "password", CLOUDMANAGERS_CONFIG_FILE)
	
#-----------------------------------------------------------------------------

def _create_VM(res_id, attributes, dict_vm):
    conn_nova = Connection(attributes["cm_nova_url"], username="", password="")
    tenant_id, x_auth_token = _get_keystone_tokens(attributes)
    body = '{"server": {"name":"'+ dict_vm['name'].encode() + '", "imageRef":"' + dict_vm['image'].encode() + '", "key_name": "' + dict_vm['key'].encode() + '", "flavorRef":"' + dict_vm['flavor'] + '", "max_count": 1, "min_count": 1, "security_groups": [{"name": "default"}]}}'
    headers = {"Content-type": "application/json", "x-auth-token": x_auth_token.encode()}
    uri = tenant_id + "/servers"
    resp = conn_nova.request_post(uri, body=body, headers=headers)
    status = resp[u'headers']['status']
    if status == '200' or status == '304':
        data = json.loads(resp['body'])
        print "vm creee et get_status vaut", _get_status(attributes)
        return _get_status(attributes)
    else:
        print 'Error http status code: ',status
        
#-----------------------------------------------------------------------------

def _delete_VM(attributes):
    conn = Connection(attributes["cm_nova_url"], username="", password="")
    tenant_id, x_auth_token = _get_keystone_tokens(attributes)
    vm = _get_VM(attributes)
    vm_id = vm['id']
    resp = conn.request_delete("/" + tenant_id +"/servers/" + vm_id, args={}, headers={'content-type':'application/json', 'accept':'application/json', 'x-auth-token':x_auth_token})

    return _get_status(attributes)

#-----------------------------------------------------------------------------

def _get_keystone_tokens(attributes):
    conn = Connection(keystone_base_url)
    body = '{"auth": {"tenantName":"'+ attributes["cm_tenant_name"] + '", "passwordCredentials":{"username": "' + attributes["cm_username"] + '", "password": "' + attributes["cm_password"] + '"}}}'
    resp = conn.request_post("/tokens", body=body, headers={'Content-type':'application/json'})
    status = resp[u'headers']['status']
    if status == '200' or status == '304':
        data = json.loads(resp['body'])
        tenant_id = data['access']['token']['tenant']['id']
        x_auth_token = data['access']['token']['id']
        return tenant_id, x_auth_token
    else:
        print 'Error status code: ',status
        
#-----------------------------------------------------------------------------

def _get_readable_status(num_status):
    return num_status
    
#-----------------------------------------------------------------------------
def _get_status(attributes):
    try:
        vm = _get_VM(attributes)
        return vm['status']
    except (ResourceException, 'pas de statut'):
        return 0
#-----------------------------------------------------------------------------
def _exists(attributes):
    try:
        _get_VM(attributes)
        return True
    except ResourceException:
        return False
#-----------------------------------------------------------------------------

def _start(attributes):
    '''
    Starts a VM.

    @param attributes: the dictionary of the attributes that will be used to
                        start a virtual machine
    @type attributes: dict
    '''
    vm = _get_VM(attributes)

    if vm.isActive() != 1:
        vm.create()

    else:
        raise ResourceException("The VM is already running")

    return _get_status(attributes)

#-----------------------------------------------------------------------------

def _shutdown(attributes):
    '''
    Shuts down a VM.

    @param attributes: the dictionary of the attributes that will be used to
                        shutdown a virtual machine
    @type attributes: dict
    '''
    vm = _get_VM(attributes)

    if vm.isActive() == 1:
        vm.shutdown()

    else:
        raise ResourceException("The VM is not running")

    return _get_status(attributes)

#-----------------------------------------------------------------------------

def _shutoff(attributes):
    '''
    Shuts off a VM.

    @param attributes: the dictionary of the attributes that will be used to
                        shutoff a virtual machine
    @type attributes: dict
    '''
    vm = _get_VM(attributes)

    if vm.isActive() == 1:
        vm.destroy()

    else:
        raise ResourceException("The VM is not running")

    return _get_status(attributes)

#-----------------------------------------------------------------------------

def _reboot(attributes):
    '''
    Reboots a VM.

    @param attributes: the dictionary of the attributes that will be used to
                        reboot a virtual machine
    @type attributes: dict
    '''
    vm = _get_VM(attributes)

    if vm.isActive() == 1:
        vm.reboot(0)

    else:
        raise ResourceException("The VM is not running")

    return _get_status(attributes)

#-----------------------------------------------------------------------------

def _pause(attributes):
    '''
    Pauses a VM.

    @param attributes: the dictionary of the attributes that will be used to
                        pause a virtual machine
    @type attributes: dict
    '''
    vm = _get_VM(attributes)

    if vm.isActive():
        vm.suspend()

    else:
        raise ResourceException("The VM must be running")

    return _get_status(attributes)

#-----------------------------------------------------------------------------
