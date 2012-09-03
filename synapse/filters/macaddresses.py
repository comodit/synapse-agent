import os


def check(mac_addresses):
    ifconfig = os.popen('ifconfig').readlines()
    found = False
    for line in ifconfig:
        for ma in mac_addresses:
            if ma in line:
                found = True
                break
    return found
