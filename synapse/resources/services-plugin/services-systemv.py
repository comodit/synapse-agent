import os

from synapse.syncmd import exec_cmd
from synapse.synapse_exceptions import ResourceException


def start(name):
    ret = exec_cmd("/etc/init.d/{0} start".format(name))
    if ret['returncode'] != 0:
        raise ResourceException(ret['stderr'])


def stop(name):
    ret = exec_cmd("/etc/init.d/{0} stop".format(name))
    if ret['returncode'] != 0:
        raise ResourceException(ret['stderr'])


def enable(name):
    ret = exec_cmd("/sbin/chkconfig {0} on".format(name))
    if ret['returncode'] != 0:
        raise ResourceException(ret['stderr'])


def disable(name):
    ret = exec_cmd("/sbin/chkconfig {0} off".format(name))
    if ret['returncode'] != 0:
        raise ResourceException(ret['stderr'])


def restart(name):
    ret = exec_cmd("/etc/init.d/{0} restart".format(name))
    if ret['returncode'] != 0:
        raise ResourceException(ret['stderr'])


def reload(name):
    ret = exec_cmd("/etc/init.d/{0} reload".format(name))
    if ret['returncode'] != 0:
        raise ResourceException(ret['stderr'])


def is_enabled(name):
    ret = exec_cmd("/sbin/runlevel")
    if ret['returncode'] != 0:
        raise ResourceException(ret['stderr'])

    match = False
    try:
        runlevel = ret['stdout'].split()[1]
        for filename in os.listdir('/etc/rc%s.d' % runlevel):
            if name in filename and filename.startswith('S'):
                match = True

    except (ValueError, IndexError), err:
        raise ResourceException(err)

    return match


def is_running(name):
    ret = exec_cmd("/etc/init.d/{0} status".format(name))
    return ret['returncode'] == 0
