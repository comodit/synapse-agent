import re
from netifaces import interfaces, ifaddresses, AF_INET


def check(ipaddresses):
    match = False
    ips = {}
    for ifaceName in interfaces():
        addresses = [i['addr']
                     for i in ifaddresses(ifaceName).setdefault(AF_INET,
                                                [{'addr':'No IP addr'}])]
        if len(addresses):
            ips[ifaceName] = addresses[0]
    for ip in ipaddresses:
        newip = ip.replace(".", "\.")
        newip = newip.replace("*", ".*")
        regex = re.compile(newip)
        for value in ips.values():
            if re.match(regex, value):
                return True

    return match
