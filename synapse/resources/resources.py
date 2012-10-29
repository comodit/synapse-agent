import time
import threading
import datetime

from Queue import Full

from synapse.synapse_exceptions import ResourceException
from synapse.config import config
from synapse.logger import logger


synapse_version = "Undefined"

try:
    import synapse.version as version_mod
    if version_mod.VERSION:
        synapse_version = version_mod.VERSION
except (ImportError, AttributeError):
    pass

@logger
class ResourcesController(object):
    """This class is the mother of all resources classes.
    """
    __resource__ = ""
    action_map = {'create': 'Creating',
                  'read': 'Reading', 
                  'update': 'Updating',
                  'delete': 'Deleting'}

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

        self.status = {}
        self.response = {}

        # Use this lock to avoid unconsistent reads among threads, especially
        # the compliance/monitor one.
        self._lock = threading.RLock()

    def _get_monitor_interval(self):
        try:
            return int(config.monitor.get(self.__resource__,
                                     self.default_interval))
        except ValueError:
            return self.default_interval

    def _fmt_attrs(self, attrs):
        res = ''

        if isinstance(attrs, dict):
            for key, value in attrs.iteritems():
                if isinstance(value, basestring) and len(value) > 20:
                    value = ''.join(value[:20] + '...')
                res += '%s: %s, ' % (key, value)

        elif isinstance(attrs, list):
            for item in attrs:
                res += '%s, ' % item

        return res.rstrip(', ')

    def process(self, arg):
        '''This is the only resource method called by the controller.'''

        action = arg.get('action')
        params = arg.get('attributes', {}) or {}
        monitor = arg.get('monitor')

        if monitor is not None:
            params['monitor'] = monitor
        self.res_id = arg.get('id')

        if action not in self.allowed_methods:
            raise ResourceException('[%s] is not allowed or unknown' % action)

        if action != 'ping':
            msg = "[%s] %s" % (self.__resource__.upper(),
                                    self.action_map[action])
            if self.res_id:
                msg += " '%s'" % self.res_id
            if params:
                msg += " (%s)" % self._fmt_attrs(params)

            self.logger.info(msg)

        with self._lock:
            self.response = self.set_response()
            try:

                result = getattr(self, action)(res_id=self.res_id,
                                               attributes=params)

                self.response = self.set_response(result)

                if action != 'ping':
                    msg = "[%s] %s" % (self.__resource__.upper(),
                                       action.capitalize())
                    if self.res_id:
                        msg += " '%s'" % self.res_id
                    msg += ": OK"
                    self.logger.info(msg)

            except ResourceException, err:
                self.response = self.set_response(error='%s' % err)

                self.logger.info("[%s] %s '%s': ERROR [%s]" %
                                 (self.__resource__.upper(),
                                  action.capitalize(),
                                  self.res_id,
                                  self.response['error'].rstrip('\n')))

        # Copy the value to return
        response = self.response

        # Reset status and response
        self.response = {}
        self.status = {}

        return response

    def close(self):
        pass

    def ping(self, **kwargs):
        return {}

    def set_response(self, resp={}, **kwargs):
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

    def comply(self, monitor=True, **kwargs):
        if monitor:
            status = {}
            for key in kwargs:
                if kwargs[key] is not None:
                    status[key] = kwargs[key]
            self.persister.persist(self.set_response(status))
        elif monitor is False:
            self.persister.unpersist(self.set_response())


    def check_mandatory(self, *args):
        for arg in args:
            if not arg:
                raise ResourceException("Please provide ID")

    def monitor(self):
        raise NotImplementedError('%s monitoring not implemented'
                                  % self.__resource__)

    def _publish_status(self, res_id, state):
        if not self.publish_status:
            return

        headers = self._set_headers()
        status = {
            'id': res_id,
            'uuid': self.uuid,
            'collection': self.__resource__,
            'status': state,
            'status_message': True,
            'version': synapse_version
        }

        self.publish_queue.put((headers, status))

    def _set_headers(self):
        return {
            'headers': {'reply_exchange': self.status_exchange},
            'routing_key': self.compliance_routing_key
        }

    def _publish(self, res_id, state, response):
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
            'current_state': response,
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
