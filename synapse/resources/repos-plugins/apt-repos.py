import os


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
    repo_file = os.path.join(src_dir, name, '.conf')

    # If the file already exists, load repo into a dict
    if os.path.isfile(repo_file):
        repo = _load_repo(repo_file)

    authorized = ('url', 'distribution', 'components')
    newrepo = dict((k, v) for k, v in attributes.iteritems() 
                   if k in authorized)

    if name in repo:
        repo[name].update(newrepo)
    else:
        repo[name] = newrepo

    _dump_repo(repo)


def delete_repo(name):
    repo_file = os.path.join(src_dir, name, '.conf')
    if os.path.isfile(repo_file):
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
                tmp_repo['url'] = elements[1]
                tmp_repo['distribution'] = elements[2]
                components = elements[3:]
                if len(components):
                    tmp_repo['components'] = components

                repo[name].append(tmp_repo)

    return repo


def _dump_repo(repodict):
    for reponame, value in repodict.iteritems():
        repo_file = os.path.join(src_dir, reponame, '.conf')
        with open(repo_file, 'w') as fd:
            debstr = []
            debstr.append('deb')
            debstr.append(value['url'])
            debstr.append(value['distribution'])
            for comp in value['components']:
                debstr.append(comp)
            fd.write(' '.join(debstr))
