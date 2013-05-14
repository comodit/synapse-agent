import re

from synapse.logger import logger


perm_mapping = {"C": "create",
                "R": "read",
                "U": "update",
                "D": "delete",
                "-": ""}

log = logger(__name__)


def get(permission_file_path):
    """Reads the permissions file line by line and process them.
    Returns an array of permissions array.
    """

    permissions = []
    with open(permission_file_path, 'r') as fd:
        for index, line in enumerate(fd):
            # If line is blank, dont bother
            if not line.strip():
                continue
            try:
                permissions.append(process(line))
            except re.error:
                log.critical("There's a problem with your permissions config "
                             "file at line %d" % ((index + 1),))
                raise SystemExit

    if not len(permissions):
        log.critical("Your permissions config file is empty")
        raise SystemExit

    return permissions


def process(dirty_line):
    """This method will process lines in the permissions config file,
    build an array of permissions from it then returns it.
    """

    perm = []

    # Let's be sure we can split the line in 4 parts
    reg = re.compile('''
            \s*             # There can be whitespaces at beginning
            (\w*|\*)        # Match any alphanum or a * for username
            \s+             # Need a whitspace separator
            (\w*|\*)        # Match any alphanum or a * for collection
            \s+             # Need a whitspace separator
            \"?(.*?)\"?     # res_id can be surrounded by double quotes
            \s+             # Need a whitspace separator
            ([CRUD]{1,4}|-) # Accept any combination of CRUD or dash
            \s*             # There can be whitespaces at the end
            $               # No more than 4 groups
            ''', re.VERBOSE)

    # Try to match !
    result = reg.match(dirty_line)

    # If no match, raise REGEXP Error !
    if result is None:
        raise re.error

    # user
    perm.append(re.compile(_sanitize(result.group(1))))

    # collection
    perm.append(re.compile(_sanitize(result.group(2))))

    # res_id
    perm.append(re.compile(_sanitize(result.group(3))))

    # crud-
    perm.append([perm_mapping[p] for p in result.group(4)])

    # if user can read, user can ping
    # add it to the action list
    if 'R' in result.group(4):
        perm[3].append('ping')

    return perm


def _sanitize(item):
    newitem = item.replace('.', '\.')
    newitem = newitem.replace('*', '.*')
    return newitem


def check(permissions, user, collection, res_id):
    for perm in permissions:
        user_match = perm[0].match(user)
        collection_match = perm[1].match(collection)
        res_id_match = perm[2].match(res_id)

        # If we have a match, return authorized methods
        if (user_match and collection_match and res_id_match):
            return perm[3]

    return []
