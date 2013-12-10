import os,sys
import uuid
import time
import pika
import json
import socket
from Queue import Queue
from Queue import Empty
from ssl import CERT_REQUIRED

from synapse.config import config
from synapse.logger import logger
from synapse_exceptions import SynapseException


@logger
class AmqpColectors():
    def __init__(self, scheduler, publish_queue):
        self.publish_queue = publish_queue
        self.scheduler = scheduler
        self.host = config.colector['host']
        self.port = config.colector['port']
        self.vhost = config.colector['vhost']
        self.username = config.colector['username']
        self.password = config.colector['password']
        self.routing_key = config.colector['publish_routing_key']
        self.exchange = config.colector['exchange']
        self.timeout = config.colector['redelivery_timeout']
        self.heartbeat = config.colector['heartbeat']
        self.connection_attempts = config.colector['connection_attempts']
        self.retry_delay = config.colector['retry_delay']
        self.uuid = config.colector['uuid']
        self.use_ssl = config.colector['use_ssl']
        self.fail_if_no_peer_cert = config.colector['fail_if_no_peer_cert']
        self.ssl_port = config.colector['ssl_port']
        self.ssl_auth = config.colector['ssl_auth']
        self.keyfile = config.colector['keyfile']
        self.cacertfile = config.colector['cacertfile']
        self.certfile = config.colector['certfile']

        self.queue = self.uuid
        self.connection = None
        self.channel    = None
        self.durable    = True

        # Plain credentials
        credentials = pika.credentials.PlainCredentials(self.username, self.password)
            
        pika_options = {'host': self.host,
                        'port': self.port,
                        'virtual_host': self.vhost,
                        'credentials': credentials,
                        'connection_attempts': self.connection_attempts,
                        'retry_delay': self.retry_delay}
 
        # SSL options
        if self.use_ssl:
           pika_options['ssl'] = True
           pika_options['port'] = self.ssl_port
           if self.ssl_auth:
              pika_options['credentials'] = pika.credentials.ExternalCredentials()
              pika_options['ssl_options'] = { 
                'ca_certs': self.cacertfile,
                'certfile': self.certfile,
                'keyfile': self.keyfile,
                'cert_reqs': CERT_REQUIRED
              }   

        if self.heartbeat:
           pika_options['heartbeat_interval'] = self.heartbeat   

        self.parameters = pika.ConnectionParameters(**pika_options) 

    def connect(self):
      try:
          self.connection = pika.BlockingConnection(self.parameters)
          self.channel = self.connection.channel()
          try:
              self.channel.queue_declare(queue=self.queue, durable=self.durable)
          except:
              self.logger.debug("AMQP COLECTOR: queue seem to exist (%s)" % sys.exc_value)

      except:
          self.logger.debug("AMQP COLECTOR: connection error (%s)" % sys.exc_value)

    def close(self):
        noout = self.connection.close(verbose="no")
        self.connection = None
        self.channel    = None

    def validate(self, msg):
        _model = { 
               'uuid': self.uuid,
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
        try:
           if self.publish_queue.qsize() > 0 :
            self.connect()
            for i in range(10):
                    pt = self.publish_queue.get(False)
                    if self.channel != None and self.channel.OPEN == 2 :
                        # Send message if connected else message are lost
                        self._publish(pt)
                    else :
                        self.logger.error(dir(self.channel))
        except Empty:
           pass

        try:
           self.close()
        except:
           pass

    def _publish(self, msg):
        body = self.validate(msg)
        
        try:
            self.channel.basic_publish(exchange=self.exchange,
                      routing_key=self.queue,
                      body=json.dumps(body),
                      properties=pika.BasicProperties(
                                delivery_mode = 2, # make message persistent
                      ))
            self.logger.debug("[AMQP-COLECTOR-PUBLISHED] #%s" % body)
        except:
            self.logger.warning("AMQP COLECTOR: error on publishing (%s)" % sys.exc_type)

    def start(self):
        self.scheduler.add_job(self._check_queue, 10)
   
