import grp

from synapse.synapse_exceptions import ResourceException
from synapse.syncmd import exec_cmd


def exists(name):
    res = False
    try:
        res = format_group_info(name).get('present', False)
    except Exception:
        pass

    return res


def get_group_infos(name=None):
    if not name:
        return [format_group_info(x.gr_name) for x in grp.getgrall()]
    else:
        return format_group_info(name)


def format_group_info(name):
    d = {}
    try:
        gr = grp.getgrnam(name)
        d["present"] = True
        d["name"] = gr.gr_name
        d["members"] = gr.gr_mem
        d["gid"] = str(gr.gr_gid)
    except KeyError:
        d["present"] = False

    return d


def group_add(name, gid):
    cmd = ["/usr/sbin/groupadd"]

    if gid:
        cmd += ['--gid', "%s" % gid]

    cmd.append(name)

    ret = exec_cmd(' '.join(cmd))

    # retcode 9 is group already exists. That's what we want.
    if ret['returncode'] != 9 and ret['returncode'] != 0:
        raise ResourceException(ret['stderr'])


def group_mod(name, new_name, gid):
    cmd = ["/usr/sbin/groupmod"]

    if new_name:
        cmd += ['--new-name', "%s" % new_name]

    if gid:
        cmd += ['--gid', "%s" % gid]

    cmd.append(name)

    ret = exec_cmd(' '.join(cmd))

    if ret['returncode'] != 0:
        raise ResourceException(ret['stderr'])


def group_del(name):
    ret = exec_cmd("/usr/sbin/groupdel %s" % name)

    # retcode 6 is group doesn't exist. That's what we want.
    if ret['returncode'] != 6 and ret['returncode'] != 0:
        raise ResourceException(ret['stderr'])
