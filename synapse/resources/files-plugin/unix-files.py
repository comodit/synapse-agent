import os
import hashlib
import datetime
import pwd
import grp

from synapse.synapse_exceptions import ResourceException


def exists(path):
    try:
        open(path)
        return True
    except IOError:
        return False


def list_dir(path):
    if not os.path.exists(path):
        raise ResourceException("Folder not found, sorry !")

    return os.listdir(path)


def get_content(path):
    path = os.path.join("/", path)
    if not os.path.exists(path):
        raise ResourceException('File not found, sorry !')

    with open(path, 'rb') as file:
        content = file.read()

    return content


def set_content(path, content):
    _path = os.path.join("/", path)

    if not os.path.exists(_path):
        raise ResourceException('File not found')

    if content is not None:
        with open(_path, 'w') as fd:
            fd.write(str(content))


def md5(path, block_size=2 ** 20):
    if not os.path.exists(path) and not os.path.isfile(path):
        raise ResourceException('File not found')
    with open(path, 'r') as f:
        md5 = hashlib.md5()
        while True:
            data = f.read(block_size)
            if not data:
                break
            md5.update(data)
        return md5.hexdigest()


def md5_str(content):
    m = hashlib.md5()
    m.update(content)
    return m.hexdigest()


def create_file(id):
    try:
        # Recursive mkdirs if dir path is not complete
        os.makedirs(os.path.dirname(os.path.join("/", id)))
        update_meta(id, -1, -1, 0755)
    except:
        pass

    # Create the file with default values if not existing
    path = os.path.join("/", id)
    if not os.path.exists(path):
        open(path, 'a').close()
        try:
            os.chmod(path, 0644)
            os.chown(path, 0, 0)
        except ValueError:
            raise
    else:
        raise ResourceException('File already exists')


def update_meta(id, owner, group, filemode):

    try:
        os.makedirs(os.path.dirname(os.path.join("/", id)), 0775)
    except:
        pass
    try:
        # Create the file if not existing
        path = os.path.join("/", id)
        if not os.path.exists(path):
            create_file(path)
        # Update the file properties
        if owner != -1:
            owner = pwd.getpwnam(owner)[3]
        if group != -1:
            group = pwd.getpwnam(group)[3]
        if filemode != -1:
            # mod from chmod is written in base 8
            filemode = int(filemode, 8)
        else:
            filemode = int(mode(path), 8)
        try:
            os.chmod(path, filemode)
            os.chown(path, owner, group)
        except ValueError:
            raise
    except (KeyError, ValueError, ResourceException), err:
        raise ResourceException(err)


def delete(path):
    _path = os.path.join("/", path)
    if not os.path.exists(_path):
        raise ResourceException('File not found, sorry !')
    os.remove(_path)


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
        user = pwd.getpwuid(uid)
        return user[0]
    except KeyError, e:
        return "Not found: ", str(e)


def group(path):
    if not os.path.exists(path):
        raise ResourceException('File does not exist.')
    si = os.stat(path)
    gid = si.st_gid
    try:
        _group = grp.getgrgid(gid)
        return _group[0]
    except KeyError, e:
        return "Not found: ", str(e)


def mode(path):
    if not os.path.exists(path):
        raise ResourceException('File does not exist.')
    si = os.stat(path)
    _mode = "%o" % si.st_mode
    return _mode[2:]
