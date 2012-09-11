import os
import hashlib
import datetime

from synapse.synapse_exceptions import ResourceException
from synapse.syncmd import exec_cmd


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

    with open(path, 'r') as file:
        content = file.read()

    return content


def set_content(path, content):
    _path = os.path.join("/", path)

    if not os.path.exists(_path):
        raise ResourceException('File not found')

    with open(_path, 'w') as fd:
        fd.write(str(content))


def md5(path, block_size=2 ** 20):
    if not os.path.exists(path):
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
        except ValueError:
            raise
    else:
        raise ResourceException('File already exists')


def update_meta(id, owner, group, mode):
    pass


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
    pass


def group(path):
    pass


def mode(path):
    pass


def execute(cmd):
    return exec_cmd(cmd)
