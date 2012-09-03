import logging
import socket

from netifaces import interfaces, ifaddresses, AF_INET, AF_LINK

from synapse.config import config

controller_options = config.controller
distribution_name = controller_options['distribution_name']
distribution_version = controller_options['distribution_version']
log = logging.getLogger('synapse.hosts')


def get_uuid():
    return config.rabbitmq['uuid']


def ping():
    return get_uuid()


def get_platform():
    return distribution_name, distribution_version


def get_hostname():
    try:
        response = socket.gethostbyaddr(socket.gethostname())[0]
    except IOError:
        response = socket.gethostname()
    except Exception, error:
        response = 'Error: ' + str(error)
    return str(response)


def get_mac_addresses():
    macs = {}
    for ifaceName in interfaces():
        addresses = [i['addr'] for i in
                ifaddresses(ifaceName).setdefault(AF_LINK,
                    [{'addr':'No MAC addr'}])]
        if len(addresses):
            macs[ifaceName] = addresses[0]
    return macs


def get_memtotal():
    controller_config = config.controller
    if controller_config['distribution_name'] != 'windows':
        memtotal = ''
        try:
            with open('/proc/meminfo', 'rb') as fd:
                lines = fd.readlines()
                memtotal = lines[0].split()[1]
        except OSError, err:
            return "{0}".format(err)
        return memtotal


def get_ip_addresses():
    ips = {}
    for ifaceName in interfaces():
        addresses = [i['addr']
                     for i in ifaddresses(ifaceName).setdefault(AF_INET,
                                                [{'addr':'No IP addr'}])]
        if len(addresses):
            ips[ifaceName] = addresses[0]
    return ips


def get_uptime():
    controller_config = config.controller
    if controller_config['distribution_name'] != 'windows':
        try:
            with open("/proc/uptime", "rb") as fd:
                out = fd.readline().split()

        except:
            return "Cannot open /proc/uptime"

        total_seconds = float(out[0])

        # Helper vars:
        MINUTE = 60
        HOUR = MINUTE * 60
        DAY = HOUR * 24

        # Get the days, hours, etc:
        days = int(total_seconds / DAY)
        hours = int((total_seconds % DAY) / HOUR)
        minutes = int((total_seconds % HOUR) / MINUTE)
        seconds = int(total_seconds % MINUTE)

        # Build up the pretty string (like this: "N days, N hours, N minutes,
        # N seconds")
        string = ""
        if days > 0:
            string += str(days) + " " + (days == 1 and "day" or "days") + ", "
        if len(string) > 0 or hours > 0:
            string += str(hours) + " " + (hours == 1 and "hour" or "hours") + \
                      ", "
        if len(string) > 0 or minutes > 0:
            string += str(minutes) + " " + \
                      (minutes == 1 and "minute" or "minutes") + ", "
        string += str(seconds) + " " + (seconds == 1 and "second" or "seconds")

        return string
