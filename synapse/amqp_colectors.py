import os,sys
import uuid
import time
import pika
import json
import socket
from amqp import Amqp
from Queue import Queue
from Queue import Empty
from ssl import CERT_REQUIRED
from threading import Thread

from synapse.config import config
from synapse.logger import logger
from synapse_exceptions import SynapseException


@logger
class AmqpColectors(Amqp,Thread):
    def __init__(self, conf, scheduler, publish_queue):
        super(AmqpColectors, self).__init__(conf)
        Thread.__init__(self, name="AMQP-COLECTORS")
        self.publish_queue = publish_queue
        self.scheduler = scheduler
        self.conf = conf
        self.state = None
 
    def validate(self, msg):
        _model = { 
               'uuid': self.conf['uuid'],
               'resource_id': '', 
               'collection': '', 
               'status': {}, 
               'version':config.SYNAPSE_VERSION
             }   
        if not isinstance(msg, dict):
           raise ValueError("Outgoing message is not a dict.  %s " % msg)
 
        try:
           _model.update(msg)
           msg = json.dumps(_model)
        except AttributeError as err:
           raise ValueError("Message not well formatted: %s", err)

        return msg

    def _check_queue(self, callback=None):
        """ check internal queue content for message to publish
        """
        if self._connection:
           try:
              if self.publish_queue.qsize() > 0 :
                 for i in range(10):
                    pt = self.publish_queue.get(False)
                    if self._publish_channel != None :
                        self._publish(pt)
                    else :
                        self.logger.debug("[AMQP-COLECTOR] Can't publish: not connected")
           except Empty:
              pass

           self._connection.add_timeout(.1, self._check_queue)

    def _publish(self, msg):
        body = self.validate(msg)
        
        try:
            self._publish_channel.basic_publish(exchange=self.exchange,
                      routing_key=self.queue,
                      body=json.dumps(body),
                      properties=pika.BasicProperties(
                                delivery_mode = 2, # make message persistent
                      ))
            self.logger.debug("[AMQP-COLECTOR-PUBLISHED] #%s" % body)
        except:
            self.logger.error("AMQP COLECTOR: error on publishing (%s)" % sys.exc_value)


    def run(self):
        self.logger.info("[AMQP] Connecting...")
        self._connection = self.connect()
        self._message_number = 0
        self._connection.ioloop.start()

    def setup_consume_channel(self):
        """ setup_consume_channel """
        self.logger.debug('setup_consume_channel: not used')

    def on_queue_declare_ok(self, queue):
        self.logger.debug("[AMQP] Queue %s binding ok." % queue.method.queue)
        self.queue = queue.method.queue
        self._check_queue()

    def setup_publish_channel(self):
        self._publish_channel.exchange_declare(exchange=self.exchange,exchange_type=self.conf['type'])
        result = self._publish_channel.queue_declare(self.on_queue_declare_ok, exclusive=True)

