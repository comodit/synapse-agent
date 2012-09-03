import sys
import urllib2
import tempfile
import subprocess

from netifaces import interfaces, ifaddresses, AF_LINK


def _get_mac_addresses():
    macs = {}
    for ifaceName in interfaces():
        addresses = [i['addr'] for i in
                ifaddresses(ifaceName).setdefault(AF_LINK,
                    [{'addr':'No MAC addr'}])]
        if len(addresses):
            macs[ifaceName] = addresses[0]
    return macs


if __name__ == "__main__":
    mac_addresses = _get_mac_addresses().values()

    if not len(mac_addresses):
        sys.exit()

    fd, tmppath = tempfile.mkstemp()

    for mac in mac_addresses:
        try:
            url = "http://alder.angleur.guardis.be/w2k8boot.py"
            #url = "http://birch.angleur.guardis.be:8000/api/data/%s/w2k8boot"
            #% (_get_mac_addresses().values()[0], tmppath)
            u = urllib2.urlopen(url)
        except urllib2.HTTPError, err:
            continue

    with open(tmppath, "wb") as tmpscript:
        tmpscript.write(u.read())

    cmd = "python %s" % tmppath

    p = subprocess.Popen(cmd.split(), stdout=subprocess.PIPE,
                         stderr=subprocess.PIPE)
    stdout, stderr = p.communicate()
    print stdout
