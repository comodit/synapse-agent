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
    d = {}
    try:
        pw = pwd.getpwnam(name)
        d["present"] = True
        d["gid"] = pw.pw_gid
        d["uid"] = pw.pw_uid
        d["name"] = pw.pw_name
        d["homedir"] = pw.pw_dir
        d["shell"] = pw.pw_shell
        d["gecos"] = pw.pw_gecos
        d["groups"] = get_groups(name)

    except KeyError:
        d["present"] = False

    return d


def user_add(name, password, login_group, groups,
             homedir, comment, uid, gid, shell):

    cmd = ['/usr/sbin/useradd']

    if login_group:
        cmd += ['-g', login_group]
    if len(groups):
        cmd += ['-G', ','.join(groups)]
    if homedir:
        cmd += ['--home', homedir]
    if comment:
        cmd += ['--comment', comment]
    if uid:
        cmd += ['--uid', uid]
    if gid:
        cmd += ['--gid', gid]
    if shell:
        cmd += ['--shell', shell]

    cmd.append(name)

    ret = exec_cmd(' '.join(cmd))

    # retcode 9 is group already exists. That's what we want.
    if ret['returncode'] != 9 and ret['returncode'] != 0:
        raise ResourceException(ret['stderr'])

    if password:
        set_password(name, password)


def filter_existing_groups(groups):
    if isinstance(groups, basestring):
        groups = groups.split(',')
        groups = [group.strip() for group in groups]

    return groups


def get_groups(name):
    cmd = ["/usr/bin/groups"]
    cmd.append(name)

    ret = exec_cmd(' '.join(cmd))
    if ret['returncode'] != 0:
        raise ResourceException(ret['stderr'])

    # Return a list of groups
    return ret['stdout'].split(':')[1].lstrip().split()


def user_mod(name, password, login_group, groups, homedir, move_home,
             comment, uid, gid, shell):

    try:
        if password:
            set_password(name, password)

        cmd = ["/usr/sbin/usermod"]
        if login_group:
            cmd += ['-g', login_group]
        if len(groups):
            cmd += ['-G', ','.join(groups)]
        if homedir:
            cmd += ['--home', homedir]
        if homedir and move_home:
            cmd += ['--move-home', move_home]
        if comment:
            cmd += ['--comment', comment]
        if uid:
            cmd += ['--uid', uid]
        if gid:
            cmd += ['--gid', gid]
        if shell:
            cmd += ['--shell', shell]

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

    # retcode 6 is group doesn't exist. That's what we want.
    if ret['returncode'] != 6 and ret['returncode'] != 0:
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

def get_pw(name):
    pw = None
    try:
        with open('/etc/shadow', 'r') as fd:
            for line in fd:
                if line.split(':')[0] == name:
                    pw = line.split(':')[1]
    except Exception as err:
        raise ResourceException(err)

    return pw
