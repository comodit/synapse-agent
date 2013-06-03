import json
import traceback

from threading import Thread
from synapse.synapse_exceptions import ResourceException

from synapse.resource_locator import ResourceLocator
from synapse.config import config
from synapse.logger import logger
from synapse.scheduler import SynSched
from synapse.alerts import AlertsController
from synapse.task import IncomingMessage, OutgoingMessage, AmqpTask
from synapse import compare

@logger
class Controller(Thread):
    '''The controller is the link between the transport layer and the
    resources layer. Basically, its job is to load resources modules and
    objects and to call their generic "process" method.
    '''

    def __init__(self, tq=None, pq=None):

        self.logger.debug("Initializing the controller...")
        Thread.__init__(self, name="CONTROLLER")

        self.tq = tq
        self.pq = pq

        self.scheduler = SynSched()
        self.locator = ResourceLocator(pq)
        self.alerter = AlertsController(self.locator, self.scheduler, pq)
        self.logger.debug("Controller successfully initialized.")

    def start_scheduler(self):
        # Start the scheduler thread
        self.scheduler.start()
        self.alerter.start()

        # Prepopulate tasks from config file
        if config.monitor['enable_monitoring']:
            self._enable_monitoring()
        if config.compliance['enable_compliance']:
            self._enable_compliance()

    def _get_monitor_interval(self, resource):
        try:
            default_interval = config.monitor['default_interval']
            return int(config.monitor.get(resource, default_interval))
        except ValueError:
            return default_interval

    def _get_compliance_interval(self, resource):
        try:
            default_interval = config.compliance['default_interval']
            return int(config.compliance.get(resource, default_interval))
        except ValueError:
            return default_interval

    def _enable_monitoring(self):
        resources = self.locator.get_instance()
        for resource in resources.values():
            if not len(resource.states):
                continue
            interval = self._get_monitor_interval(resource.__resource__)
            self.scheduler.add_job(resource.monitor_states, interval)

    def _enable_compliance(self):
        resources = self.locator.get_instance()
        for resource in resources.values():
            if not len(resource.states):
                continue
            interval = self._get_compliance_interval(resource.__resource__)
            self.scheduler.add_job(resource.check_compliance, interval)

    def stop_scheduler(self):
        # Shutdown the scheduler/monitor
        self.logger.debug("Shutting down global scheduler...")
        if self.scheduler.isAlive():
            self.scheduler.shutdown()
            self.scheduler.join()
        self.logger.debug("Scheduler stopped.")

    def close(self):

        # Stop this thread by putting a stop message in the blocking queue get
        self.tq.put("stop")

       # Close properly each resource
        try:
            for resource in self.locator.get_instance().itervalues():
                resource.close()
        except ResourceException, e:
            self.logger.debug(str(e))

        self.stop_scheduler()

    def run(self):
        """Implementation of the Threading run method. This methods waits on
        the tasks queue to get messages from the transport layer and then calls
        the call_method. It then waits for a response to put into the publish
        queue before waiting for a new task to come.
        """

        self.logger.debug("Controller started.")

        response = {}
        while True:
            task = self.tq.get()
            if task == "stop":
                break
            try:
                response = self.call_method(task.sender, task.body)

            except ResourceException as err:
                self.logger.error("%s" % err)

                if response.get('status'):
                    del response['status']
                response['error'] = '%s' % err

            except Exception:
                self.logger.debug('{0}'.format(traceback.format_exc()))

            finally:
                self.pq.put(AmqpTask(response, headers=task.headers))

    def call_method(self, user, body):
        """Reads the collection the message needs to reach and then calls the
        process method of that collection. It returns the response built by the
        collection.
        """
        response = {}

        # Check if the message body contains filters.
        filters = body.get('filters')

        if filters:
            if not self._check_filters(filters):
                raise ResourceException("Filters did not match")

        try:
            # Get a reference to the corresponding resource object.
            instance = self.locator.get_instance(body['collection'])

            # Call the resource's generic process method
            response = instance.process(body)

        except ResourceException, err:
            self.logger.debug("Resource exception: %s" % err)
            response['error'] = '%s' % err

        except Exception, e:
            raise ResourceException("There's a problem with your %s plugin: %s"
                                    % (body['collection'], e))

        # Return the response
        return response

    def _check_filters(self, filters):
        self.logger.debug("Checking filters")
        match = False

        for key, value in filters.iteritems():
            try:
                module = 'synapse.filters.%s' % key
                m = __import__(module)
                parts = module.split('.')
                for comp in parts[1:]:
                    m = getattr(m, comp)

                match = m.check(value)
                if match == False:
                    break
            except ImportError:
                pass

        self.logger.debug("Filters match: %s" % match)
        return match
