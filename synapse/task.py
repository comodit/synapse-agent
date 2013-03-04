import json

from pika import BasicProperties
from synapse.config import config


class Task(object):
    def __init__(self, headers, body):
        self.headers = headers
        self.body = self.get_body(body)

        self.user_id = self.get_user_id()
        self.reply_exchange = self.get_reply_exchange()
        self.reply_to = self.get_reply_to()
        self.correlation_id = self.get_corr_id()
        self.redeliver = True

    def get_user_id(self):
        return self.headers.get('user_id', '')

    def get_reply_exchange(self):
        re = ''
        if 'headers' in self.headers:
            hds = self.headers['headers']
            if isinstance(hds, dict):
                re = hds.get('reply_exchange', '')

        return re

    def get_reply_to(self):
        return self.headers.get('reply_to', 
                                self.headers.get('routing_key', ''))
        
    def get_corr_id(self):
        return self.headers.get('correlation_id')

    def get_body(self, body):
        return json.loads(body)



class PublishTask(Task):
    def get_body(self, body):
        return json.dumps(body)

    def get_user_id(self):
        return config.rabbitmq['username'] or None

    def get_properties(self):
        return {
            'correlation_id': self.get_corr_id(),
            'user_id': self.get_user_id()
        }

    def get(self):
        return {
            "exchange": self.reply_exchange,
            "routing_key": self.reply_to,
            "properties": BasicProperties(**self.get_properties()),
            "body": self.body
        }
