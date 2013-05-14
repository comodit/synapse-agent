import datetime
import grp
import hashlib
import os
import pwd
import logging

from synapse.synapse_exceptions import ResourceException
log = logging.getLogger('synapse.unix-files')


def exists(path):
    try:
        return os.path.exists(path)
    except IOError:
        return False


def is_file(path):
    try:
        return os.path.isfile(path)
    except IOError:
        return False


def list_dir(path):
    if not os.path.exists(path):
        raise ResourceException("Folder not found, sorry !")

    return os.listdir(path)


def get_content(path):
    if not os.path.exists(path):
        raise ResourceException('File not found, sorry !')

    with open(path, 'rb') as fd:
        content = fd.read()

    return content


def set_content(path, content):
    if not is_file(path):
        raise ResourceException('File not found')

    if content is not None:
        with open(path, 'w') as fd:
            fd.write(str(content))


def md5(path, block_size=2 ** 20):
    if not os.path.isfile(path):
        return None

    with open(path, 'r') as f:
        md5 = hashlib.md5()
        while True:
            data = f.read(block_size)
            if not data:
                break
            md5.update(data)
        return md5.hexdigest()


def md5_str(content):
    if content is None:
        content = ''

    m = hashlib.md5()
    m.update(content)
    return m.hexdigest()


def create_file(path):
    # Create folders if they don't exist
    if not os.path.exists(os.path.dirname(path)):
        create_folders(os.path.dirname(path))

    # Create the file if it does not exist
    if not os.path.exists(path):
        open(path, 'a').close()


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


def delete(path):
    try:
        os.remove(path)
    except OSError:
        log.debug('File %s does not exist', path)


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
    if os.path.isfile(path):
        _mode = 0666 ^ current_umask
    return oct(_mode)
