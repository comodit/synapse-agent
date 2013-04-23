import sys
import time
import signal
import socket
import traceback

from Queue import Queue

from synapse.scheduler import SynSched
from synapse.amqp import Amqp
from synapse.config import config
from synapse.controller import Controller
from synapse.logger import logger
from synapse.synapse_exceptions import ResourceException


@logger
class Dispatcher(object):
    """This module dispatches commands incoming from the command line to
    specific transports. It is also responsible for starting threads and
    catching signals like SIGINT and SIGTERM.
    """

    def __init__(self, transport):

        self.transport = transport

        # Handle signals
        signal.signal(signal.SIGINT, self.stop)
        signal.signal(signal.SIGTERM, self.stop)

        # Threads instances variables
        self.controller = None
        self.sched = None
        self.amqpsynapse = None

        self.resourcefile = None

        # These queues will be shared between the controller and the
        # transport and are used for incoming tasks and responses
        self.pq = Queue()
        self.tq = Queue()

    def stop(self, signum, frame):
        """This method handles SIGINT and SIGTERM signals. """

        self.logger.info("Stopping due to signal #%d" % signum)
        raise KeyboardInterrupt

    def stop_synapse(self):
        """Closes all threads and exits properly.
        """
        if self.resourcefile:
            self.resourcefile.done = True

        # Close the controller and wait for it to quit
        if self.controller:
            if self.controller.isAlive():
                self.controller.close()
                self.controller.join()
                self.logger.debug("Controller thread stopped")

        # Shutdown the scheduler/monitor
        if self.sched:
            if self.sched.isAlive():
                self.sched.shutdown()
                self.sched.join()
                self.logger.debug("Scheduler stopped")

        self.logger.info("Successfully stopped.")

    def dispatch(self):
        """This method actually dispatches to specific transport methods
        according to command line parameters.
        """

        self.logger.info('Starting on %s transport' %
                         self.transport.capitalize())
        transports = {
                'amqp': self.start_amqp,
                'http': self.start_resourcefile,
                'file': self.start_resourcefile,
                }
        try:
            transports[self.transport]()
        except KeyError as err:
            self.logger.error("Transport unknown. [%s]" % err)
            self.stop_synapse()
            sys.exit()

    def start_amqp(self):
        """Starts all needed threads: scheduler, controller and AMQP transport
        IOLOOP.
        """

        retry_timeout = config.rabbitmq['retry_timeout']
        try:

            self.sched = SynSched()
            self.controller = Controller(self.sched, self.tq, self.pq)
            self.controller.start()
            self.sched.start()

            self.amqpsynapse = Amqp(config.rabbitmq, pq=self.pq, tq=self.tq)

            while True:
                try:
                    self.amqpsynapse.run()
                except socket.error as err:
                    self.logger.error("Cannot connect to broker (%s)" % err)
                    self.logger.info("Retrying in %d seconds" % retry_timeout)
                    time.sleep(retry_timeout)

        except KeyboardInterrupt:
            pass
        except ResourceException as err:
            self.logger.error(str(err))
        except Exception as err:
            self.logger.error(err)
        finally:
            self.amqpsynapse.stop()
            self.stop_synapse()

    def start_resourcefile(self):
        """This method handles the --uri file and --uri http commands.
        """

        from synapse.resourcefile import ResourceFile
        try:
            self.resourcefile = ResourceFile(self.transport)
            self.resourcefile.fetch()
        except KeyboardInterrupt:
            self.stop_synapse()
