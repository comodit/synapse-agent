import sys
import time
import signal
import socket

from Queue import Queue

from synapse.scheduler import SynSched
from synapse.amqp import AmqpSynapse, AmqpAdmin, AmqpError
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
        self.force_close = False

        # Handle signals
        #signal.signal(signal.SIGINT, self.stop)
        signal.signal(signal.SIGTERM, self.stop)

        # Threads instances variables
        self.controller = None
        self.sched = None

        self.resourcefile = None

        # These queues will be shared between the controller and the
        # transport and are used for incoming tasks and responses
        self.publish_queue = Queue()
        self.tasks_queue = Queue()

    def stop(self, signum, frame):
        """This method handles SIGINT and SIGTERM signals. """

        self.logger.debug("Stopping due to signal #%d" % signum)
        self.stop_synapse()

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

        self.force_close = True
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
        except (AttributeError, KeyError), err:
            self.logger.error("Transport unknown. [%s]" % err)
            self.stop_synapse()
            sys.exit()

    def start_amqp(self):
        """Starts all needed threads: scheduler, controller and AMQP transport
        IOLOOP.
        """

        retry_timeout = config.rabbitmq['retry_timeout']
        try:
            self.amqpadmin = AmqpAdmin(config.rabbitmq)
            while not self.force_close:
                try:
                    self.amqpadmin.connect()
                    break
                except (socket.timeout, IOError) as err:
                    self.logger.error(err)
                    try:
                        self.logger.debug("Sleeping %d sec" % retry_timeout)
                        time.sleep(retry_timeout)
                    except KeyboardInterrupt:
                        self.stop_synapse()
                        raise SystemExit
                except AmqpError as err:
                    break
                except KeyboardInterrupt:
                    self.stop_synapse()
                    raise SystemExit

            self.sched = SynSched()
            self.controller = Controller(scheduler=self.sched,
                                         tasks_queue=self.tasks_queue,
                                         publish_queue=self.publish_queue)
            # Start the controller
            self.controller.start()

            # Start the scheduler
            self.sched.start()

            self.amqpsynapse = AmqpSynapse(config.rabbitmq,
                                           publish_queue=self.publish_queue,
                                           tasks_queue=self.tasks_queue)
            while not self.force_close:
                try:
                    self.amqpsynapse.connect()
                except (AmqpError, IOError) as err:
                    self.logger.error(err)
                    try:
                        self.logger.debug("Sleeping %d sec" % retry_timeout)
                        time.sleep(retry_timeout)
                    except KeyboardInterrupt:
                        self.stop_synapse()
                except KeyboardInterrupt:
                    self.stop_synapse()

        except SystemExit:
            pass

        except ResourceException as err:
            self.logger.error(str(err))

    def start_resourcefile(self):
        """This method handles the --uri file and --uri http commands.
        """

        from synapse.resourcefile import ResourceFile
        try:
            self.resourcefile = ResourceFile(self.transport)
            self.resourcefile.fetch()
        except KeyboardInterrupt:
            self.stop_synapse()
