import cm_util
from synapse.config import config
from synapse.syncmd import exec_cmd
from synapse.resources.resources import ResourceException

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
