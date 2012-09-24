from synapse.syncmd import exec_cmd
from synapse.synapse_exceptions import ResourceException


def start(name):
    ret = exec_cmd("net start {0}".format(name))
    if ret['returncode'] != 0:
        raise ResourceException(ret['stderr'])


def stop(name):
    ret = exec_cmd("net stop {0}".format(name))
    if ret['returncode'] != 0:
        raise ResourceException(ret['stderr'])


def enable(name):
    ret = exec_cmd("sc config {0} start= auto".format(name))
    if ret['returncode'] != 0:
        raise ResourceException(ret['stderr'])


def disable(name):
    ret = exec_cmd("sc config {0} start= demand".format(name))
    if ret['returncode'] != 0:
        raise ResourceException(ret['stderr'])


def restart(name):
    stop(name)
    start(name)


def reload(name):
    pass


def is_enabled(name):
    pass


def is_running(name):
    ret = exec_cmd("sc query {0}".format(name))
    for line in ret['stdout'].split('\n'):
        if 'RUNNING' in line:
            return True
    return False
