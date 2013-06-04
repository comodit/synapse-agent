import json

from pika import BasicProperties
from synapse.config import config
from synapse.logger import logger
from synapse import permissions


@logger
class Message(object):
    _model = {}

    def __init__(self, message):
        self.body = self.validate(message)

    def validate(self, message):
        raise NotImplementedError


class OutgoingMessage(Message):

    def __init__(self,
                 resource_id='',
                 collection='',
                 status={},
                 msg_type='',
                 **kwargs):
        msg = {
            'resource_id': resource_id,
            'collection': collection,
            'status': status,
            'msg_type': msg_type
        }

        for kwarg in kwargs:
            msg[kwarg] = kwargs[kwarg]

        self.body = self.validate(msg)

    def validate(self, msg):
        _model = {
            'uuid': config.rabbitmq['uuid'],
            'resource_id': '',
            'collection': '',
            'status': {},
            'version':config.SYNAPSE_VERSION
        }

        if not isinstance(msg, dict):
            raise ValueError("Outgoing message is not a dict.")

        try:
            _model.update(msg)
            msg = json.dumps(_model)
        except AttributeError as err:
            raise ValueError("Message not well formatted: %s", err)

        return msg


class IncomingMessage(Message):

    def validate(self, msg):
        _model = {
            'id': '',
            'collection': '',
            'action': '',
            'attributes': {},
            'monitor': False
        }

        try:
            msg = json.loads(msg)
            _model.update(msg)
        except AttributeError as err:
            raise ValueError("Message not well formatted: %s", err)

        if 'collection' not in msg or not msg['collection']:
            raise ValueError("Collection missing.")

        if 'action' not in msg or not msg['action']:
            raise ValueError("Action missing.")

        if 'attributes' in msg and not isinstance(msg['attributes'], dict):
            raise ValueError("Attributes must be a dict.")

        if 'monitor' in msg and not isinstance(msg['monitor'], bool):
            raise ValueError("Monitor must be a boolean")

        return _model


@logger
class Task(object):
    def __init__(self, message, sender='', check_permissions=True):
        self.body = message.body
        self.sender = sender
        #TODO: re-enable permission
        #if check_permissions and isinstance(message, IncomingMessage):
        #    self._check_permissions(message.body)

    def _check_permissions(self, msg):
        allowed = permissions.get(config.controller['permissions_path'])
        perms = permissions.check(allowed,
                                  self.sender,
                                  msg['collection'],
                                  msg['id'])

        if self.body['action'] not in perms:
            raise ValueError("You don't have permission to do that.")


@logger
class AmqpTask(Task):
    def __init__(self, body, headers={}):
        self.headers = headers
        self.sender = self._get_sender(self.headers)
        super(AmqpTask, self).__init__(body, sender=self.sender)
        self.user_id = self._get_user_id()
        self.correlation_id = self._get_correlation_id(self.headers)
        self.delivery_tag = self._get_delivery_tag(self.headers)
        self.publish_exchange = self._get_publish_exchange(self.headers)
        self.routing_key = self._get_routing_key(self.headers)
        self.redeliver = False

    def _get_publish_exchange(self, headers):
        publish_exchange = None

        if 'headers' in headers:
            hds = headers['headers']
            if isinstance(hds, dict):
                publish_exchange = hds.get('reply_exchange')

        if publish_exchange is None:
            publish_exchange = config.rabbitmq['publish_exchange']

        return publish_exchange

    def _get_delivery_tag(self, headers):
        return headers.get('delivery_tag')

    def _get_routing_key(self, headers):
        routing_key = headers.get('reply_to', headers.get('routing_key'))

        if routing_key is None:
            routing_key = config.rabbitmq['publish_routing_key']

        return routing_key

    def _get_correlation_id(self, headers):
        return headers.get('correlation_id')

    def _get_sender(self, headers):
        return headers.get('user_id') or ''

    def _get_user_id(self):
        return config.rabbitmq['username']

    def get(self):
        basic_properties = BasicProperties(correlation_id=self.correlation_id,
                                           user_id=self.user_id)
        body = self.body
        if isinstance(body, dict):
            body = json.dumps(self.body)
        try:
            return {"exchange": self.publish_exchange,
                    "routing_key": self.routing_key,
                    "properties": basic_properties,
                    "body": body}
        except ValueError as err:
            self.logger.error("Invalid message (%s)" % err)
