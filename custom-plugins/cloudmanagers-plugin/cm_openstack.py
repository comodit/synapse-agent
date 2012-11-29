import cm_util
from synapse.config import config
from synapse.syncmd import exec_cmd
from synapse.resources.resources import ResourceException
import json
from restful_lib import Connection
import ConfigParser

from synapse.logger import logger
from synapse.syncmd import exec_cmd

#-----------------------------------------------------------------------------

def _get_VMs():
    '''
    Returns all virtual machines for the given connection.

    @param connection: a connection to libvirt
    @type connection: libvirt.virConnect instance
    '''
    VMs = [connection.lookupByID(x).name() for x in
               connection.listDomainsID()]
    return VMs + connection.listDefinedDomains()

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
    flavor = _get_flavor(vm_id)
    return flavor['vcpus']
    
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
	
#-----------------------------------------------------------------------------

def _create_VM(res_id, attributes, dict_vm):
    conn_nova = Connection(nova_base_url, username="", password="")
    tenant_id, x_auth_token = _get_keystone_tokens(tenant_name, username, password)
    body = '{"server": {"name":"'+ dict_vm['name'].encode() + '", "imageRef":"' + dict_vm['image'].encode() + '", "key_name": "' + dict_vm['key'].encode() + '", "flavorRef":"' + dict_vm['flavor'] + '", "max_count": 1, "min_count": 1, "security_groups": [{"name": "default"}]}}'
    headers = {"Content-type": "application/json", "x-auth-token": x_auth_token.encode()}
    uri = tenant_id + "/servers"
    print 'body vaut', body
    print 'headers vaut', headers
    print 'uri vaut', uri
    resp = conn_nova.request_post(uri, body=body, headers=headers)
    status = resp[u'headers']['status']
    if status == '200' or status == '304':
        data = json.loads(resp['body'])
        print "vm creee et get_status vaut", _get_status(connection, attributes)
        return _get_status(connection, attributes)
    else:
        print 'Error http status code: ',status
        
#-----------------------------------------------------------------------------

def _get_keystone_tokens(tenant_name, username, password):
    conn = Connection(keystone_base_url)
    body = '{"auth": {"tenantName":"'+ tenant_name + '", "passwordCredentials":{"username": "' + username + '", "password": "' + password + '"}}}'
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
