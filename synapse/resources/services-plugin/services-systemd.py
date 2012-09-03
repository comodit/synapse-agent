from synapse.syncmd import exec_cmd
from synapse.synapse_exceptions import ResourceException


def _cmd(action, name):
    return "systemctl {0} {1}.service".format(action, name)


def start(name):
    ret = exec_cmd(_cmd("start", name))
    if ret['returncode'] != 0:
        raise ResourceException(ret['stderr'])


def stop(name):
    ret = exec_cmd(_cmd("stop", name))
    if ret['returncode'] != 0:
        raise ResourceException(ret['stderr'])


def enable(name):
    ret = exec_cmd(_cmd("enable", name))
    if ret['returncode'] != 0:
        raise ResourceException(ret['stderr'])


def disable(name):
    ret = exec_cmd(_cmd("disable", name))
    if ret['returncode'] != 0:
        raise ResourceException(ret['stderr'])


def restart(name):
    ret = exec_cmd(_cmd("restart", name))
    if ret['returncode'] != 0:
        raise ResourceException(ret['stderr'])


def reload(name):
    ret = exec_cmd(_cmd("reload", name))
    if ret['returncode'] != 0:
        raise ResourceException(ret['stderr'])


def is_enabled(name):
    ret = exec_cmd(_cmd("is-enabled", name))
    return ret['returncode'] == 0


def is_running(name):
    ret = exec_cmd(_cmd("status", name))
    return ret['returncode'] == 0
