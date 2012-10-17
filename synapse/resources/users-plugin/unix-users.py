import re
import grp
import pwd

from synapse.synapse_exceptions import ResourceException
from synapse.syncmd import exec_cmd


def user_exists(name):
    try:
        get_user_infos(name)

    except ResourceException:
        return False

    return True


def get_user_infos(name):
    try:
        pw = pwd.getpwnam(name)
        d = {}
        d["gid"] = pw.pw_gid
        d["uid"] = pw.pw_uid
        d["name"] = pw.pw_name
        d["dir"] = pw.pw_dir
        d["shell"] = pw.pw_shell
        d["gecos"] = pw.pw_gecos
        d["groups"] = get_groups(name)
        return d

    except KeyError:
        raise ResourceException("User not found")


def user_add(name, password, login_group, groups,
             homedir, comment, uid, gid, shell):
    cmd = []
    cmd.append("/usr/sbin/useradd")

    if login_group:
        cmd = cmd + ['-g', login_group]

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

    if homedir:
        cmd = cmd + ['--home', homedir]

    if comment:
        cmd = cmd + ['--comment', comment]

    if uid:
        cmd = cmd + ['--uid', uid]

    if gid:
        cmd = cmd + ['--gid', gid]

    if shell:
        cmd = cmd + ['--shell', shell]

    cmd.append(name)

    ret = exec_cmd(' '.join(cmd))

    if ret['returncode'] != 0:
        raise ResourceException(ret['stderr'])

    if password:
        set_password(name, password)


def filter_existing_groups(groups):
    if isinstance(groups, basestring):
        groups = groups.split(',')
        groups = [group.strip() for group in groups]

    return groups


def get_groups(name):
    cmd = []
    cmd.append("/usr/bin/groups")
    cmd.append(name)

    ret = exec_cmd(' '.join(cmd))
    if ret['returncode'] != 0:
        raise ResourceException(ret['stderr'])

    # Return a list of groups
    return ret['stdout'].split(':')[1].lstrip().split()


def user_mod(name, password, login_group, add_to_groups, remove_from_groups,
             set_groups, homedir, move_home, comment, uid, gid, shell):

    try:
        if password:
            set_password(name, password)

        cmd = ["/usr/sbin/usermod"]

        if login_group:
            cmd = cmd + ['-g', login_group]

        elif add_to_groups:
            groups = filter_existing_groups(add_to_groups)
            if len(groups):
                cmd = cmd + ['-G', ','.join(groups), '-a']

        elif remove_from_groups:
            groups = filter_existing_groups(remove_from_groups)
            current_groups = get_groups(name)

            if len(groups):
                groups_to_set = filter(lambda x: x not in groups,
                                       current_groups)
                cmd = cmd + ['-G', ','.join(groups_to_set)]

        elif set_groups:
            groups = filter_existing_groups(set_groups)
            if len(groups):
                cmd = cmd + ['-G', ','.join(groups)]

        if homedir:
            cmd = cmd + ['--home', homedir]
            if move_home:
                cmd = cmd + ['--move-home', move_home]

        if comment:
            cmd = cmd + ['--comment', comment]

        if uid:
            cmd = cmd + ['--uid', uid]

        if gid:
            cmd = cmd + ['--gid', gid]

        if shell:
            cmd = cmd + ['--shell', shell]

        cmd.append(name)
        if len(cmd) > 2:
            ret = exec_cmd(' '.join(cmd))
            if ret['returncode'] != 0:
                raise ResourceException(ret['stderr'])

    except ResourceException:
        raise


def set_password(name, password):
    ret = exec_cmd("echo {0}:{1} | chpasswd".format(name, password))
    if ret['returncode'] != 0:
        raise ResourceException(ret['stderr'])


def user_del(name):
    ret = exec_cmd("/usr/sbin/userdel {0} -f".format(name))
    if ret['returncode'] != 0:
        raise ResourceException(ret['stderr'])


def get_group_infos(name):
    try:
        gr = grp.getgrnam(name)
        d = {}
        d["name"] = gr.gr_name
        d["members"] = gr.gr_mem
        d["gid"] = gr.gr_gid
        return d

    except KeyError:
        raise ResourceException("Group not found")
