import os
import logging

from synapse.syncmd import exec_cmd
from synapse.synapse_exceptions import ResourceException


env_vars = {'DEBIAN_FRONTEND': 'noninteractive'}
os.environ.update(env_vars)

log = logging.getLogger('synapse')

def install(name):
    ret = exec_cmd("/usr/bin/apt-get -qy update")
    ret = exec_cmd("/usr/bin/apt-get -qy install {0} --force-yes".format(name))
    if not is_installed(name):
        raise ResourceException(ret['stderr'])


def get_installed_packages():
    ret = exec_cmd("/usr/bin/dpkg-query -l")
    return ret['stdout'].split('\n')


def remove(name):
    ret = exec_cmd("/usr/bin/apt-get -qy remove {0} --force-yes".format(name))
    if ret['returncode'] != 0:
        raise ResourceException(ret['stderr'])


def update(name):
    if name:
        ret = exec_cmd(
            "/usr/bin/apt-get -quy install {0} --force-yes".format(name))
        if ret['returncode'] != 0:
            raise ResourceException(ret['stderr'])
    else:
        ret = exec_cmd("/usr/bin/apt-get -qy update")
        ret = exec_cmd("/usr/bin/apt-get -qy upgrade --force-yes")
        if ret['returncode'] != 0:
            raise ResourceException(ret['stderr'])


def is_installed(name):
    ret = exec_cmd("/usr/bin/dpkg-query -l '{0}'".format(name))
    if ret['returncode'] != 0:
        return False

    # There's no way to use return code of any of the dpkg-query options.
    # Instead we use the "state" column of dpkg-query -l
    # So programmaticaly here:
    # 1. Get stdout
    # 2. Split on new line
    # 3. Get the last but one line (last is blank, in any case?)
    # 4. Get first character (i=installed)
    try:
        return ret['stdout'].split('\n')[-2][0] == 'i'
    except IndexError as err:
        log.error(err)
        return False
