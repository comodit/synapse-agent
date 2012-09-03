import grp

from synapse.synapse_exceptions import ResourceException
from synapse.syncmd import exec_cmd


def get_group_infos(name=None):
    if not name:
        return [format_group_info(x.gr_name) for x in grp.getgrall()]
    else:
        return format_group_info(name)


def format_group_info(name):
    try:
        gr = grp.getgrnam(name)
        d = {}
        d["name"] = gr.gr_name
        d["members"] = gr.gr_mem
        d["gid"] = gr.gr_gid
        return d
    except KeyError:
        raise ResourceException("Group not found")


def group_add(name):
    ret = exec_cmd("/usr/sbin/groupadd {0}".format(name))
    if ret['returncode'] != 0:
        raise ResourceException(ret['stderr'])


def group_mod(name, new_name):
    ret = exec_cmd("/usr/sbin/groupmod -n {0} {1}".format(new_name, name))
    if ret['returncode'] != 0:
        raise ResourceException(ret['stderr'])


def group_del(name):
    ret = exec_cmd("/usr/sbin/groupdel {0}".format(name))
    if ret['returncode'] != 0:
        raise ResourceException(ret['stderr'])
