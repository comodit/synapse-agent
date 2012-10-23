from synapse.syncmd import exec_cmd
from synapse.synapse_exceptions import ResourceException
from synapse.logger import logger

log = logger('yum-pkg')


def install(name):
    ret = exec_cmd("/usr/bin/yum -q -y install %s" % name)
    if ret['returncode'] != 0:
        raise ResourceException(ret['stderr'])


def get_installed_packages():
    ret = exec_cmd("/bin/rpm -qa")
    return ret['stdout'].split('\n')


def remove(name):
    ret = exec_cmd("/usr/bin/yum -q -y remove %s" % name)
    if ret['returncode'] != 0:
        raise ResourceException(ret['stderr'])


def update(name):
    # We need to check first if the package is installed. yum update of a
    # non-existing package has a returncode of 0. We need to raise an exception
    # if the package is not installed !
    inst = is_installed(name)
    ret = exec_cmd("/usr/bin/yum -q -y update %s" % name)

    if ret['returncode'] != 0 or not inst:
        raise ResourceException(ret['stderr'])


def is_installed(name):
    if name:
        ret = exec_cmd("/bin/rpm -q %s" % name)
        return ret['returncode'] == 0
    else:
        return get_installed_packages()
