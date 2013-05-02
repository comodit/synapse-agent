import os

from synapse.synapse_exceptions import ResourceException

src_dir = "/etc/apt/sources.list.d"


def get_repos(name, details=False):
    repos = []
    for src_file in os.listdir(src_dir):
        full_path = os.path.join(src_dir, src_file)
        if name and name == src_file.split('.')[0]:
            repos.append(_load_repo(full_path))
            break
        elif name is None:
            repos.append(_load_repo(full_path))

    return repos


def create_repo(name, attributes={}):
    # Initialize the repo dictionnary
    repo = {}
    repo_file = os.path.join(src_dir, name + '.list')

    # If the file already exists, load repo into a dict
    if os.path.isfile(repo_file):
        repo = _load_repo(repo_file)

    newrepo = {}

    try:
        # baseurl attr is mandatory
        baseurl = attributes['baseurl']

        # if the full entry is not provided (i.e "deb url dist [components]")
        # distribution and components attr are mandatory
        if not _full_entry(baseurl):
            url = baseurl
            distribution = attributes['distribution']
            components = attributes['components']
            if not isinstance(components, list):
                components = set(''.join(components.split()).split(','))

        # If the full entry is provided, just split it into required elements
        else:
            url = baseurl.split()[0]
            distribution = baseurl.split()[1]
            components = set(baseurl.split()[2:])

        # Build the new repo dict
        newrepo = {'baseurl': url,
                   'distribution': distribution,
                   'components': components}

    except KeyError as err:
        raise ResourceException("Missing mandatory attribute [%s]" % err)

    # If that repo already exist, del entry and add the new one
    if name in repo:
        for index, rep in enumerate(repo[name]):
            if (rep['baseurl'] == newrepo['baseurl'] and
                rep['distribution'] == newrepo['distribution']):

                del repo[name][index]

        repo[name].append(newrepo)
    else:
        repo[name] = [newrepo]

    _dump_repo(repo)


def _full_entry(entry):
    items = entry.split()
    if len(items) == 1:
        return False
    elif len(items) >= 2:
        return True
    else:
        raise ResourceException("Invalid baseurl attribute.")


def delete_repo(name, attributes):
    repo = {}
    repo_file = os.path.join(src_dir, name + '.list')

    # If the file already exists, load repo into a dict
    if os.path.isfile(repo_file):
        repo = _load_repo(repo_file)

    try:
        # baseurl attr is mandatory
        baseurl = attributes['baseurl']

        if len(baseurl.split()) == 1:
            url = baseurl
            distribution = attributes['distribution']

        elif len(baseurl.split()) > 1:
            url = baseurl.split()[0]
            distribution = baseurl.split()[1]

        # Build the new repo dict
        deleterepo = {'baseurl': url,
                      'distribution': distribution}

    except KeyError as err:
        raise ResourceException("Missing mandatory attribute [%s]" % err)

    if name in repo:
        for index, rep in enumerate(repo[name]):
            if (rep['baseurl'] == deleterepo['baseurl'] and
                rep['distribution'] == deleterepo['distribution']):

                del repo[name][index]

        if not len(repo[name]):
            os.remove(repo_file)


def _load_repo(full_path):
    name = full_path.split(os.path.sep)[-1].split('.')[0]
    repo = {name: []}

    with open(full_path, 'r') as fd:
        for line in fd:
            tmp_repo = {}
            if not line:
                break
            elements = line.split()
            if len(elements) > 1 and elements[0] == 'deb':
                tmp_repo['baseurl'] = elements[1]
                tmp_repo['distribution'] = elements[2]
                components = elements[3:]
                if len(components):
                    tmp_repo['components'] = components

                repo[name].append(tmp_repo)

    return repo


def _dump_repo(repodict):
    for reponame, repos in repodict.iteritems():
        repo_file = os.path.join(src_dir, reponame + '.list')
        with open(repo_file, 'w') as fd:
            for item in repos:
                debstr = []
                debstr.append('deb')
                debstr.append(item['baseurl'])
                debstr.append(item['distribution'])
                for comp in item['components']:
                    debstr.append(comp)
                fd.write(' '.join(debstr) + '\n')
