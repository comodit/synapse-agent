import sys
import traceback
import time
import datetime

from synapse.synapse_exceptions import ResourceException
from synapse.config import config
from synapse.logger import logger
from synapse.task import PublishTask


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

        # This queue is injected by the resource locator at plugin
        # instantiation
        self.publish_queue = None

        self.response = {}

        # Use this lock to avoid unconsistent reads among threads, especially
        # the compliance/monitor one.
        self._lock = False

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

        self._lock = True
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

        except ResourceException as err:
            self.response = self.set_response(error='%s' % err)
            self.logger.info("[%s] %s '%s': RESOURCE ERROR [%s]" %
                             (self.__resource__.upper(),
                              action.capitalize(),
                              self.res_id,
                              self.response['error'].rstrip('\n')))
        except Exception as err:
            self.response = self.set_response(error='%s' % err)
            traceback.print_exc(file=sys.stdout)
            self.logger.info("[%s] %s '%s': UNKNOWN ERROR [%s]" %
                             (self.__resource__.upper(),
                              action.capitalize(),
                              self.res_id,
                              self.response['error'].rstrip('\n')))
        finally:
            self._lock = False

        # Copy the value to return
        response = self.response

        # Reset status and response
        self.response = {}

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
            'collection': self.__resource__,
            'msg_type': 'response'
        }

        for key in kwargs:
            if kwargs[key] is not None:
                response[key] = kwargs[key]

        return response

    def add_job(self, interval):
        if self.scheduler:
            self.scheduler.add_job(self.monitor, interval)

    def watch(self):
        if self.scheduler:
            try:
                interval = self._get_monitor_interval()
                self.scheduler.add_job(self.monitor_manager, interval)
                self.scheduler.add_job(self.check_compliance, interval)
                #if self.__resource__ == 'hosts':
                #    self.scheduler.add_job(self.monitor, interval)

            except NotImplementedError:
                pass

    def comply(self, res_id=None, current_status=None, monitor=True, **kwargs):
        if monitor:
            # Retrieve the persisted status
            status = self.find(self.__resource__, res_id)

            # Update persisted status with additional arguments
            for key in kwargs:
                if kwargs[key] is not None:
                    status[key] = kwargs[key]

            # Set last compliant, last not compliant in status
            compliant = status.get('compliant')
            if compliant:
                status['last_compliant'] = datetime.datetime.now()
            elif compliant is False:
                status['last_not_compliant'] = datetime.datetime.now()

            # Update current status if it's provided
            response = self.set_response(status)
            if current_status:
                response.update({'current_status': current_status})

            # Persist the response
            self.persister.persist(response)

        # If monitor is set to False, unpersist the resource
        elif monitor is False:
            self.persister.unpersist(self.set_response())

    def find(self, collection, res_id):
        result = {}
        try:
            res_list = getattr(self.persister, self.__resource__)
            for item in res_list:
                if item.get('resource_id') == res_id:
                    result = item
        except AttributeError:
            pass

        return result

    def check_mandatory(self, *args):
        for arg in args:
            if not arg:
                raise ResourceException("Please provide ID")

    def monitor_manager(self):
        if self._lock:
            return
        try:
            persisted_list = getattr(self.persister, self.__resource__)
            for item in persisted_list:
                current_state = {}
                persisted_state = item['status']
                try:
                    current_state = self.read(res_id=item['resource_id'])
                except ResourceException as err:
                    self.logger.error(err)

                compliant = self.monitor(persisted_state, current_state)

                if compliant != item.get('compliant'):
                    item['back_to_compliance'] = True
                else:
                    item['back_to_compliance'] = False

                # Build / update the dict to be persisted
                item['current_status'] = current_state
                item['compliant'] = compliant
                if compliant:
                    item['last_compliant'] = datetime.datetime.now()
                elif compliant is False:
                    item['last_not_compliant'] = datetime.datetime.now()

                self.persister.persist(item)

        except AttributeError:
            pass

    def monitor(self, persisted_state, current_state):
        raise NotImplementedError('%s monitoring not implemented'
                                  % self.__resource__)

    def _publish_status(self, res_id, state):
        if not self.publish_status:
            return

        headers = self._set_headers()
        status = {'id': res_id,
                  'uuid': self.uuid,
                  'collection': self.__resource__,
                  'status': state,
                  'status_message': True,
                  'msg_type': 'status',
                  'version': synapse_version}

        pt = PublishTask(headers, status)
        pt.redeliver = False
        self.publish_queue.put(pt)

    def _set_headers(self, redeliver=True):
        return {'headers': {'reply_exchange': self.status_exchange},
                'routing_key': self.compliance_routing_key}

    def check_compliance(self):
        try:
            res = getattr(self.persister, self.__resource__)
        except AttributeError:
            return

        for state in res:
            lc = state.get('last_compliant')
            lnc = state.get('last_not_compliant')
            compliant = state.get('compliant')

            # Last compliant, last not compliant and compliant must be defined
            if lnc is None:
                continue

            elif lc is None and lnc is not None:
                self._publish_compliance(state['resource_id'], state,
                                     state['current_status'],
                                     last_alert=state.get('last_alert'),
                                     compliant=compliant,
                                     b2c=state.get('back_to_compliance'))
                continue

            if lc > lnc:
                if state.get('back_to_compliance'):
                    self._publish_compliance(state['resource_id'], state,
                                         state['current_status'],
                                         last_alert=state.get('last_alert'),
                                         compliant=compliant,
                                         b2c=True)

            elif lc < lnc:
                self._publish_compliance(state['resource_id'], state,
                                         state['current_status'],
                                         last_alert=state.get('last_alert'),
                                         compliant=compliant)

    def _publish_compliance(self, res_id, state, response, last_alert=None,
                            compliant=None, b2c=False):
        """When a state change is detected, this method publish a message to
        the transport layer"""

        if not self.enable_compliance:
            return

        timestamp = time.strftime('%d/%m/%y %H:%M:%S', time.localtime())

        headers = self._set_headers()
        msg_type = 'compliance_ok' if compliant else 'compliance_error'

        compliance = {'id': res_id,
                      'uuid': self.uuid,
                      'collection': state['collection'],
                      'expected_state': state['status'],
                      'current_state': response,
                      'msg_type': msg_type,
                      'timestamp': timestamp}

        # If the resource is back to compliance
        if b2c:
            self.publish_queue.put(PublishTask(headers, compliance))
            if 'last_alert' in state:
                del state['last_alert']
                self.persister.persist(state)
            self.logger.info("[COMPLIANCE] [%s] %s is BACK to "
                             "compliance" % (compliance['collection'],
                                             compliance['id']))
        elif not compliant:
            if last_alert:
                delta = datetime.datetime.now() - last_alert
                if delta > datetime.timedelta(seconds=self.alert_interval):
                    state['last_alert'] = datetime.datetime.now()
                    self.persister.persist(state)
                    self.publish_queue.put(PublishTask(headers, compliance))
                    self.logger.info("[COMPLIANCE] [%s] %s is NOT compliant" %
                                     (compliance['collection'],
                                      compliance['id']))
            else:
                state['last_alert'] = datetime.datetime.now()
                self.persister.persist(state)
                self.publish_queue.put(PublishTask(headers, compliance))
                self.logger.info("[COMPLIANCE] [%s] %s is NOT compliant" %
                                 (compliance['collection'],
                                  compliance['id']))
