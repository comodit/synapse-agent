import ConfigParser
import os

from synapse.synapse_exceptions import ResourceException


repo_path = "/etc/yum.repos.d"


def get_repos(name, details=False):

    repos = {}
    repo_file_list = os.listdir(repo_path)

    for repo_file in repo_file_list:
        repo_file_path = os.path.join(repo_path, repo_file)
        config = ConfigParser.RawConfigParser()
        try:
            config.read(repo_file_path)
            for section in config.sections():
                repo = dict(config.items(section))
                repo["filename"] = repo_file_path
                repo["present"] = True
                repos[section] = repo
        except Exception:
            repo = {'present': False}

    response = repos

    if name:
        response = repos.get(name, {"present": False,
                                    "name": name})
    else:
        if not details:
            response = repos.keys()

    return response


def create_repo(name, attributes):

    config_parser = ConfigParser.RawConfigParser()

    values = ("name",
              "baseurl",
              "metalink",
              "mirrorlist",
              "gpgcheck",
              "gpgkey",
              "exclude",
              "includepkgs",
              "enablegroups",
              "enabled",
              "failovermethod",
              "keepalive",
              "timeout",
              "enabled",
              "http_caching",
              "retries",
              "throttle",
              "bandwidth",
              "sslcacert",
              "sslverify",
              "sslclientcert",
              "metadata_expire",
              "mirrorlist_expire",
              "proxy",
              "proxy_username",
              "proxy_password",
              "cost",
              "skip_if_unavailable")

    baseurl = None
    try:
        baseurl = attributes['baseurl'].split()[0]
    except (KeyError, AttributeError) as err:
        raise ResourceException("Wrong baseurl attribute [%s]" % err)

    # Check if repo already exists
    repo = get_repos(name)

    # If it exists, get the filename in which the repo is defined
    # If not, check if a filename is user provided
    # If no filename is provided, create one based on the repo name
    if repo.get('present'):
        filename = repo.get("filename")
    elif attributes.get("filename"):
        filename = attributes["filename"]
    else:
        filename = "%s.repo" % name

    # Read the config file (empty or not) and load it in a ConfigParser
    # object
    repo_file_path = os.path.join(repo_path, filename)
    config_parser.read(repo_file_path)

    # Check if the repo is define in the ConfigParser context.
    # If not, add a section based on the repo name.
    if not config_parser.has_section(name):
        config_parser.add_section(name)
        config_parser.set(name, "name", name)

    # Set gpgcheck to 0 by default to bypass some issues
    config_parser.set(name, 'gpgcheck', 0)

    # Update the section with not None fields provided by the user
    for key, value in attributes.items():
        if value is not None and key in values:
            config_parser.set(name, key, value)

    config_parser.set(name, 'baseurl', baseurl)

    # Write changes to the repo file.
    with open(repo_file_path, 'wb') as repofile:
        config_parser.write(repofile)


def delete_repo(name, attributes):
    config_parser = ConfigParser.RawConfigParser()
    repo = get_repos(name)

    if repo.get('present'):
        filename = repo.get("filename")
        repo_file_path = os.path.join(repo_path, filename)
        config_parser.read(repo_file_path)

        if config_parser.remove_section(name):
            # Write changes to the repo file.
            with open(repo_file_path, 'wb') as repofile:
                config_parser.write(repofile)

        # Delete the repo file if there are no section in them
        config_parser.read(repo_file_path)
        if not len(config_parser.sections()):
            os.remove(repo_file_path)
