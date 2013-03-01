import sys
import logging
import optparse
import urlparse
import traceback
from synapse.config import config
from synapse import logger

from synapse.dispatcher import Dispatcher
from synapse.daemon import Daemon

synapse_version = "Undefined"

try:
    import synapse.version as version_mod
    if version_mod.VERSION:
        synapse_version = version_mod.VERSION
except (ImportError, AttributeError):
    pass


def init_parser():

    parser = optparse.OptionParser(version=synapse_version)

    parser.add_option("--daemonize", "-d", action="store_true",
                      dest="daemonize", default=False,
                      help="Starts in daemon")

    parser.add_option("--uri", type="string", dest="uri", default='amqp',
                      help="Specify where to get jobs from.")

    parser.add_option("--vhost", action="store",
                      dest="vhost", default=None,
                      help="Overrides config file's vhost option")

    parser.add_option("--uuid", action="store",
                      dest="uuid", default=None,
                      help="Overrides config file's queue option")

    parser.add_option("--disable", action="store",
                      dest="disable", default=None,
                      help="Comma separated list of resources to disable")

    parser.add_option("--force", action="store_true",
                      dest="force", default=None,
                      help="Force the ssl dance to take place by "
                            "deleting .pem files. Use with care !")

    parser.add_option("--timeout", action="store", type='int',
                      dest="timeout", default=None,
                      help='Will try to access http file for this number of '
                           'seconds')

    parser.add_option("-v", action="store_true",
                      dest="verbose", default=None,
                      help="Set loglevel to debug.")

    parser.add_option("--trace", action='store_true',
                      dest='trace', default=False,
                      help="Show traceback")

    parser.add_option("--print-config", action="store_true",
                      dest="print_config", default=False,
                      help="Prints the configuration on console")

    return parser


class Main(object):
    def __init__(self, parse_commandline=True):
        # Initialize the parser
        self.parser = init_parser()

        # Update config with command line options
        logger.setup_logging(config.log)
        self.logger = logging.getLogger('synapse')
        self.transport = None
        self.daemon = SynapseDaemon(config.paths['pid'])

        try:
            cli_args = sys.argv[1:] if parse_commandline else []
            options, args = self.parser.parse_args(cli_args)
            loglevel = config.log['level']
            if options.verbose:
                loglevel = 'DEBUG'
            self.setup_logger(loglevel)
            self.parse_commandline(options, args)

            # Daemonize process ?
            if options.daemonize:
                self.daemon.set_transport(self.transport)
                self.daemon.start()
            else:
                Dispatcher(self.transport).dispatch()

        except Exception as err:
            self.logger.error(err)
            if options.trace:
                self.logger.error('{0}'.format(traceback.format_exc()))
            sys.exit(-1)

    def parse_commandline(self, options, args):

        try:
            from synapse import bootstrap
            config.add_section('bootstrap', bootstrap.get_bootstrap_config())
        except ImportError:
            pass

        if options.print_config:
            print config.dump_config_file(to_file=False)
            sys.exit()

        # Handle Daemon
        if len(args):
            if args[0].lower() == 'stop':
                self.daemon.stop()
                sys.exit()
            elif args[0].lower() == 'status':
                is_running = self.daemon.status()
                if is_running:
                    self.logger.info('Running !')
                else:
                    self.logger.info('Not Running !')
                sys.exit()

        if self.daemon.is_running_in_bg():
            self.logger.error("Daemon already running in background. "
                              "Exiting now.")
            sys.exit(-1)

        self.setup_transport(options)

        try:
            register = config.bootstrap.get('register', False)
            if self.transport == 'amqp' and register:
                bootstrap.bootstrap(options)
                config.dump_config_file()

        except Exception as err:
            self.logger.warning("Error while bootstraping: %s" % err)
            self.logger.warning("Trying to connect with default settings")

        self.setup_controller(options)

        return options, args

    def setup_transport(self, options):
        # Start parsing other options and arguments
        parsed_uri = urlparse.urlparse(options.uri)
        transport = parsed_uri.scheme or parsed_uri.path

        # Override RABBITMQ options
        if transport == 'amqp' or 'start':
            if options.uuid:
                config.rabbitmq['uuid'] = options.uuid
            if parsed_uri.hostname:
                config.rabbitmq['host'] = parsed_uri.hostname
            if parsed_uri.port:
                config.rabbitmq['port'] = parsed_uri.port
            if parsed_uri.username:
                config.rabbitmq['username'] = parsed_uri.username
            if parsed_uri.password:
                config.rabbitmq['password'] = parsed_uri.password
            if parsed_uri.scheme and parsed_uri.path:
                config.rabbitmq['vhost'] = parsed_uri.path[1:]

        # Override RESOURCEFILE options
        if transport == 'http':
            if options.timeout:
                config.resourcefile['timeout'] = options.timeout
            config.resourcefile['url'] = options.uri

        if transport == 'file':
            config.resourcefile['path'] = parsed_uri.path

        self.transport = transport

    def setup_controller(self, options):
        # Override CONTROLLER options
        if options.disable:
            config.controller['ignored_resources'] = options.disable

    def setup_logger(self, loglevel):
        # Override LOGGER options
        if loglevel in logger.LEVELS:
            handlers = logging.getLogger('synapse').handlers
            for handler in handlers:
                handler.setLevel(getattr(logging, loglevel))


class SynapseDaemon(Daemon):
    def run(self):
        Dispatcher(self.transport).dispatch()

    def set_transport(self, transport):
        self.transport = transport

    def status(self):
        try:
            with open(self.pidfile, 'r') as pf:
                pid = int(pf.read().strip())
        except IOError:
            pid = None
        except ValueError:
            return False

        try:
            with open("/proc/%d/status" % pid, 'r'):
                return True
        except (IOError, TypeError):
            return False

    def is_running_in_bg(self):
        return self.status()
