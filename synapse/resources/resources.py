import time
import threading
import datetime

from Queue import Full

from synapse.synapse_exceptions import ResourceException
from synapse.config import config
from synapse.logger import logger


@logger
class ResourcesController(object):
    """This class is the mother of all resources classes.
    """
    __resource__ = ""

    def __init__(self, module):
        self.default_interval = config.monitor['default_interval']
        self.alert_interval = config.monitor['alert_interval']
        self.publish_status = config.monitor['publish_status']
        self.enable_compliance = config.monitor['enable_compliance']

        self.uuid = config.rabbitmq['uuid']
        self.status_exchange = config.rabbitmq['status_exchange']
        self.status_routing_key = config.rabbitmq['status_routing_key']
        self.compliance_routing_key = config.rabbitmq['compliance_routing_key']

        self.allowed_methods = ('create', 'read', 'update', 'delete', 'ping')

        self.module = module
        self.res_id = None
        self.scheduler = None
        self.persister = None
        self.publish_queue = None

        # Use this lock to avoid unconsistent reads among threads, especially
        # the compliance/monitor one.
        self._lock = threading.RLock()

    def _get_monitor_interval(self):
        try:
            return int(config.monitor.get(self.__resource__,
                                     self.default_interval))
        except ValueError:
            return self.default_interval

    def process(self, arg):
        '''This is the only resource method called by the controller.'''

        action = arg.get('action')
        params = arg.get('attributes', {})
        monitor = arg.get('monitor')

        if monitor is not None:
            params['monitor'] = monitor
        self.res_id = arg.get('id')

        if action not in self.allowed_methods:
            raise ResourceException('Method not allowed or unknown '
                                    '[{0}]'.format(action))

        with self._lock:
            return getattr(self, action)(res_id=self.res_id, attributes=params)

    def close(self):
        pass

    def ping(self, **kwargs):
        return self.set_response({})

    def set_response(self, resp, **kwargs):
        """Use this method to send a response to the controller.
        """

        response = {
            'uuid': self.uuid,
            'resource_id': self.res_id,
            'status': resp,
            'collection': self.__resource__
        }

        for key in kwargs:
            if kwargs[key] is not None:
                response[key] = kwargs[key]

        return response

    def watch(self):
        if self.scheduler:
            try:
                interval = self._get_monitor_interval()
                self.scheduler.add_job(self.monitor, interval)
            except NotImplementedError:
                pass

    def monitor(self):
        raise NotImplementedError('%s monitoring not implemented'
                                  % self.__resource__)

    def _publish_status(self, res_id, state, message_type=None):
        if not self.publish_status:
            return

        headers = self._set_headers()
        status = {
            'id': res_id,
            'uuid': self.uuid,
            'collection': self.__resource__,
            'status': state,
            'status_message': True
        }

        self.publish_queue.put((headers, status))

    def _set_headers(self):
        return {
            'headers': {'reply_exchange': self.status_exchange},
            'routing_key': self.compliance_routing_key
        }

    def _publish(self, res_id, state, response, message_type=None):
        """When a state change is detected, this method publish a message to
        the transport layer"""

        if not self.enable_compliance:
            return

        timestamp = time.strftime('%d/%m/%y %H:%M:%S', time.localtime())

        headers = self._set_headers()

        compliance = {
            'id': res_id,
            'uuid': self.uuid,
            'collection': state['collection'],
            'expected_state': state['status'],
            'current_state': response['status'],
            'msg_type': 'compliance',
            'timestamp': timestamp
        }

        try:
            last_alert = state.get("last_alert")
            if last_alert:
                delta = datetime.datetime.now() - last_alert
                if delta > datetime.timedelta(seconds=self.alert_interval):
                    self._update_last_alert(state)
                    self.publish_queue.put((headers, compliance))
            else:
                self._update_last_alert(state)
                self.publish_queue.put((headers, compliance))
        except Full:
            pass

    def _update_last_alert(self, state):
        state.update(dict(last_alert=datetime.datetime.now()))
        self.persister.persist(state, update_alert=True)
        return state
