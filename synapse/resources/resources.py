import sys
import traceback
import time
from datetime import datetime, timedelta


from synapse.synapse_exceptions import ResourceException
from synapse.states_manager import StatesManager
from synapse.config import config
from synapse.logger import logger
from synapse.task import AmqpTask, OutgoingMessage


@logger
class ResourcesController(object):
    """ This class is the mother of all resources classes.
    """
    __resource__ = ""

    action_map = {'create': 'Creating',
                  'read'  : 'Reading',
                  'update': 'Updating',
                  'delete': 'Deleting',
    }

    def __init__(self, module):
        self.default_interval = config.monitor['default_interval']
        alert_interval = config.compliance['alert_interval']
        self.alert_interval = timedelta(seconds=alert_interval)

        self.module = module
        self.res_id = None
        self.states_manager = StatesManager(self.__resource__)
        self.states = self.states_manager.states

        # This queue is injected by the resource locator at plugin
        # instantiation
        self.publish_queue = None

        self.response = {}

        # Use this lock to avoid unconsistent reads among threads, especially
        # the compliance/monitor one.
        self._lock = False

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

        msg = "[%s] %s" % (self.__resource__.upper(), self.action_map[action])
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

            msg = "[%s] %s" % (self.__resource__.upper(), action.capitalize())
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
        self.logger.debug("Shutting down %s controller...", self.__resource__)
        self.states_manager.shutdown()

    def set_response(self, resp={}, **kwargs):
        """Use this method to send a response to the controller.
        """

        msg = OutgoingMessage(resource_id=self.res_id,
                              collection=self.__resource__,
                              status=resp,
                              msg_type='response',
                              **kwargs)

        return msg

    def check_mandatory(self, *args):
        for arg in args:
            if not arg:
                raise ResourceException("Please provide ID")

    def is_compliant(self, expected, current):
        raise NotImplementedError('%s monitoring not implemented'
                                  % self.__resource__)

    def save_state(self, res_id, state={}, monitor=True):
        self.states_manager.save_state(res_id, state, monitor)

    def check_compliance(self):
        if self._lock:
            return

        for state in self.states:
            if not state['compliant'] or state['back_to_compliance']:
                self.publish_compliance(state)

    def monitor_states(self):
        if self._lock:
            return

        for state in self.states:
            # Get expected and current states
            expected = state['status']
            res_id = state['resource_id']
            current = self.read(res_id)

            # Update current status
            state['current_status'] = current

            # Update compliance infos
            was_compliant = state['compliant']
            is_compliant = self.is_compliant(expected, current)

            state['compliant'] = is_compliant
            state['back_to_compliance'] = not was_compliant and is_compliant

            now = datetime.now()

            # Persist states on disk.
            self.states_manager.persist()

    def publish(self, message):
        if self.publish_queue:
            self.publish_queue.put(AmqpTask(message))

    def publish_compliance(self, state, publish=True):
        """ When a state change is detected, this method publish a message to
        the transport layer.
        """

        msg = ''
        now = datetime.now()
        time_format = '%d/%m/%y %H:%M:%S'
        state['timestamp'] = now.strftime(time_format)

        if state['back_to_compliance'] and state['compliant']:
            state['msg_type'] = 'compliance_ok'
            state['back_to_compliance'] = False
            state['last_alert'] = None
            msg = "is BACK to compliance"

        elif not state['compliant']:
            state['msg_type'] = 'compliance_error'
            msg = "is NOT compliant"
            last_alert = state.get('last_alert')
            if last_alert:
                delta = now - datetime.strptime(last_alert, time_format)
                if delta < self.alert_interval:
                    publish = False
                else:
                    state['last_alert'] = now.strftime(time_format)
            else:
                state['last_alert'] = now.strftime(time_format)


        if publish:
            self.logger.debug("%s (%s) %s." % (state['resource_id'],
                                               state['collection'],
                                               msg))
            msg = OutgoingMessage(**state)
            self.publish(msg)

        self.states_manager.persist()
