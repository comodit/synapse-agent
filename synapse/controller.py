import json
import traceback

from threading import Thread
from synapse.synapse_exceptions import ResourceException

from synapse.resource_locator import ResourceLocator
from synapse.config import config
from synapse import permissions
from synapse.logger import logger


@logger
class Controller(Thread):
    '''The controller is the link between the transport layer and the
    resources layer. Basically, its job is to load resources modules and
    objects and to call their generic "process" method.
    '''

    def __init__(self, scheduler=None, tasks_queue=None, publish_queue=None):

        self.logger.debug("Initializing the controller...")
        Thread.__init__(self, name="CONTROLLER")
        permissions_path = config.controller['permissions_path']

        try:
            self.permissions = permissions.get(permissions_path)
        except (IOError, OSError) as err:
            self.logger.critical(err)
            raise SystemExit

        self.uuid = config.rabbitmq['uuid']
        self.tasks_queue = tasks_queue
        self.publish_queue = publish_queue
        self.locator = ResourceLocator(scheduler, publish_queue)
        self.logger.debug("Controller successfully initialized.")

    def close(self):
        try:
            self.tasks_queue.put("stop")
            for resource in self.locator.get_instance().itervalues():
                resource.close()
        except ResourceException, e:
            self.logger.debug(str(e))

    def run(self):
        """Implementation of the Threading run method. This methods waits on
        the tasks queue to get messages from the transport layer and then calls
        the call_method. It then waits for a response to put into the publish
        queue before waiting for a new task to come.
        """

        self.logger.debug("Controller started.")

        response = {}
        while True:
            item = self.tasks_queue.get(True, 60 * 60 * 24 * 365 * 1000)

            if item == "stop":
                break

            task = None
            headers = None
            try:
                headers = item[0]
                task = json.loads(item[1])
                user_id = headers['user_id'] or ''
                response = self.call_method(user_id, task)
            except (TypeError, ValueError):
                self.logger.debug('{0}'.format(traceback.format_exc()))

            except ResourceException as err:
                self.logger.error("%s" % err)

                if response.get('status'):
                    del response['status']
                response['error'] = '%s' % err
                response['uuid'] = self.uuid

            except Exception:
                self.logger.debug('{0}'.format(traceback.format_exc()))

            finally:
                self.publish_queue.put((headers, response))

    def call_method(self, user_id, body, check_perm=True):
        """Reads the collection the message needs to reach and then calls the
        process method of that collection. It returns the response built by the
        collection.
        """
        response = {}
        # Check if collection is specified and that the resource actually
        # exists.
        if not isinstance(body, dict):
            raise ResourceException("Bad message formatting")

        # Check if the message body contains filters.
        filters = body.get('filters')
        res_id = body.get('id') or ''

        if check_perm:
            perms = permissions.check(self.permissions,
                                      user_id,
                                      body.get('collection'),
                                      res_id)

            if body.get('action') not in perms:
                raise ResourceException("You don't have permission to do "
                                        "that.")

        if filters:
            if not self._check_filters(filters):
                raise ResourceException("Filters did not match")

        collection = body.get('collection')

        # Get a reference to the corresponding resource object.
        # Check if the object isn't already instantiated.
        try:
            instance = self.locator.get_instance(collection)

            # Call the resource's generic process method
            response = instance.process(body)

            # Check if it can be dumped in JSON format
            try:
                json.dumps(response)
            except UnicodeDecodeError, err:
                raise ResourceException("Problem when decoding payload.")

        except ResourceException, err:
            self.logger.debug("Resource exception: %s" % err)
            if response.get('status'):
                del response['status']
            response['error'] = '%s' % err
            response['uuid'] = self.uuid

        except Exception, e:
            raise ResourceException("There's a problem with your %s plugin: %s"
                                    % (collection, e))

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
