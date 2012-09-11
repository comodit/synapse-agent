import re

from synapse.synapse_exceptions import ResourceException
from synapse.syncmd import exec_cmd


def user_exists(name):
    try:
        get_user_infos(name)

    except ResourceException:
        return False

    return True


def get_user_infos(name):
    pass
    #try:
    #    pw = pwd.getpwnam(name)
    #    d = {}
    #    d["gid"] = pw.pw_gid
    #    d["uid"] = pw.pw_uid
    #    d["name"] = pw.pw_name
    #    d["dir"] = pw.pw_dir
    #    d["shell"] = pw.pw_shell
    #    d["gecos"] = pw.pw_gecos
    #    d["groups"] = get_groups(name)
    #    return d

    #except KeyError:
    #    raise ResourceException("User not found")


def user_add(name, password, login_group, groups):
    cmd = []
    cmd.append("/usr/sbin/useradd")
    if login_group:
        cmd.append("-g")
        cmd.append(login_group)
    if groups:
        groups_no_ws = re.sub(r'\s', '', groups)
        try:
            group_list = groups_no_ws.split(',')
            for group in group_list:
                groups.read(group)
            cmd.append("-G")
            cmd.append(groups_no_ws)
        except ResourceException:
            raise ResourceException("Group does not exist")

    cmd.append(name)

    ret = exec_cmd(' '.join(cmd))

    if ret['returncode'] != 0:
        raise ResourceException(ret['stderr'])

    if password:
        set_password(name, password)


def filter_existing_groups(groups):
    groups_no_ws = re.sub(r'\s', '', groups)
    group_list = groups_no_ws.split(',')
    existing_groups = []
    for group in group_list:
        try:
            groups.get_group_infos(group)
            existing_groups.append(group)
        except ResourceException:
            pass

    return existing_groups


def get_groups(name):
    cmd = []
    cmd.append("/usr/bin/groups")
    cmd.append(name)

    ret = exec_cmd(' '.join(cmd))
    if ret['returncode'] != 0:
        raise ResourceException(ret['stderr'])

    # Return a list of groups
    return ret['stdout'].split(':')[1].lstrip().split()


def user_mod(name,
             password=None,
             login_group=None,
             add_to_groups=None,
             remove_from_groups=None,
             set_groups=None
             ):

    try:
        if password:
            set_password(name, password)

        cmd = []
        cmd.append("/usr/sbin/usermod")

        if login_group:
            cmd.append("-g")
            cmd.append(login_group)

        elif add_to_groups:
            groups = filter_existing_groups(add_to_groups)
            if len(groups):
                cmd.append("-G")
                cmd.append(','.join(groups))
                cmd.append("-a")

        elif remove_from_groups:
            groups = filter_existing_groups(remove_from_groups)
            current_groups = get_groups(name)

            if len(groups):
                groups_to_set = filter(lambda x: x not in groups,
                                       current_groups)
                cmd.append("-G")
                cmd.append(','.join(groups_to_set))

        elif set_groups:
            groups = filter_existing_groups(set_groups)
            if len(groups):
                cmd.append("-G")
                cmd.append(','.join(groups))

        cmd.append(name)
        if len(cmd) > 2:
            ret = exec_cmd(' '.join(cmd))
            if ret['returncode'] != 0:
                raise ResourceException(ret['stderr'])

    except ResourceException:
        raise


def set_password(name, password):
    ret = exec_cmd("echo -n {0} | passwd --stdin {1}".format(password, name))
    if ret['returncode'] != 0:
        raise ResourceException(ret['stderr'])


def user_del(name):
    ret = exec_cmd("/usr/sbin/userdel {0} -f".format(name))
    if ret['returncode'] != 0:
        raise ResourceException(ret['stderr'])


def get_group_infos(name):
    pass
    #try:
    #    gr = grp.getgrnam(name)
    #    d = {}
    #    d["name"] = gr.gr_name
    #    d["members"] = gr.gr_mem
    #    d["gid"] = gr.gr_gid
    #    return d

    #except KeyError:
    #    raise ResourceException("Group not found")
