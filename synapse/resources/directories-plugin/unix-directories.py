import datetime
import grp
import os
import pwd
import shutil

from synapse.synapse_exceptions import ResourceException


def exists(path):
    try:
        return os.path.exists(path)
    except IOError:
        return False


def is_dir(path):
    try:
        return os.path.isdir(path)
    except IOError:
        return False


def list_dir(path):
    if not os.path.exists(path):
        raise ResourceException("Folder not found, sorry !")

    return os.listdir(path)


def create_folders(path):
    try:
        # Recursive mkdirs if dir path is not complete
        os.makedirs(path)
    except OSError:
        #Already exists, no prob !
        pass
    except Exception as err:
        # Another problem
        raise ResourceException('Failed when creating folders: %s' % err)


def update_meta(path, owner, group, filemode):
    if not os.path.exists(path):
        raise ResourceException('This path does not exist.')

    ownerid = get_owner_id(owner)
    groupid = get_group_id(group)
    octfilemode = int(filemode, 8)

    try:
        os.chmod(path, octfilemode)
        os.chown(path, ownerid, groupid)
    except ValueError as err:
        raise ResourceException(err)


def delete_folder(path):
    if not os.path.exists(path):
        raise ResourceException('File not found, sorry !')
    try:
        shutil.rmtree(path)
    except OSError as err:
        raise ResourceException("Exception when removing the folder: %s" % err)


def mod_time(path):
    return str(datetime.datetime.fromtimestamp(os.path.getmtime(path)))


def c_time(path):
    return str(datetime.datetime.fromtimestamp(os.path.getctime(path)))


def owner(path):
    if not os.path.exists(path):
        raise ResourceException('File does not exist.')

    si = os.stat(path)
    uid = si.st_uid
    try:
        return pwd.getpwuid(uid).pw_name
    except KeyError as err:
        raise ResourceException(err)


def get_owner_id(name):
    try:
        return pwd.getpwnam(name).pw_uid
    except KeyError as err:
        raise ResourceException(err)


def group(path):
    if not os.path.exists(path):
        raise ResourceException('File does not exist.')

    si = os.stat(path)
    gid = si.st_gid
    try:
        return grp.getgrgid(gid).gr_name
    except KeyError as err:
        raise ResourceException(err)


def get_group_id(name):
    try:
        return grp.getgrnam(name).gr_gid
    except KeyError as err:
        raise ResourceException(err)


def mode(path):
    if not os.path.exists(path):
        raise ResourceException('File does not exist.')

    si = os.stat(path)
    _mode = "%o" % si.st_mode
    return _mode[-4:]


def get_default_mode(path):
    current_umask = os.umask(0)
    os.umask(current_umask)
    _mode = 0644
    if os.path.isdir(path):
        _mode = 0777 ^ current_umask
    return oct(_mode)
