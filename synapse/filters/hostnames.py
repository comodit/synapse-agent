import socket
import re


def check(hostnames):

    match = False
    actual_hostname = socket.gethostbyaddr(socket.gethostname())[0]

    for hostname in hostnames:
        newhostname = hostname.replace(".", "\.")
        newhostname = newhostname.replace("*", ".*")
        regex = re.compile(newhostname)
        if re.match(regex, actual_hostname):
            match = True
            break

    return match
