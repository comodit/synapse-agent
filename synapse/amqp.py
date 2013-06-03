import time
import pika
import socket

from Queue import Empty
from ssl import CERT_REQUIRED
from datetime import datetime, timedelta

from pika.adapters import SelectConnection
from pika.adapters.select_connection import SelectPoller
from pika.credentials import PlainCredentials, ExternalCredentials

from synapse.logger import logger
from synapse.task import IncomingMessage, AmqpTask


@logger
class Amqp(object):
    def __init__(self, conf):
        # RabbitMQ general options
        self.cacertfile = conf['cacertfile']
        self.certfile = conf['certfile']
        self.exchange = conf['exchange']
        self.status_exchange = conf['status_exchange']
        self.fail_if_no_peer_cert = conf['fail_if_no_peer_cert']
        self.heartbeat = conf['heartbeat']
        self.host = conf['host']
        self.keyfile = conf['keyfile']
        self.password = conf['password']
        self.port = conf['port']
        self.ssl_port = conf['ssl_port']
        self.queue = conf['uuid']
        self.retry_delay = conf['retry_delay']
        self.ssl_auth = conf['ssl_auth']
        self.use_ssl = conf['use_ssl']
        self.username = conf['username']
        self.vhost = conf['vhost']
        self.redelivery_timeout = conf['redelivery_timeout']
        self.connection_attempts = conf['connection_attempts']
        self.poller_delay = conf['poller_delay']

        # Connection and channel initialization
        self._connection = None
        self._consume_channel = None
        self._consume_channel_number = None
        self._publish_channel = None
        self._publish_channel_number = None
        self._message_number = 0
        self._deliveries = {}
        self._responses = []

        self._closing = False

        self._processing = False

        # Plain credentials
        credentials = PlainCredentials(self.username, self.password)
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
                pika_options['credentials'] = ExternalCredentials()
                pika_options['ssl_options'] = {
                    'ca_certs': self.cacertfile,
                    'certfile': self.certfile,
                    'keyfile': self.keyfile,
                    'cert_reqs': CERT_REQUIRED
                }

        if self.heartbeat:
            pika_options['heartbeat_interval'] = self.heartbeat

        self.parameters = pika.ConnectionParameters(**pika_options)

        self.print_config()

    def run(self):
        self.logger.info("[AMQP] Connecting...")
        self._connection = self.connect()
        self._message_number = 0
        self._connection.ioloop.start()

    def connect(self):
        SelectPoller.TIMEOUT = float(self.poller_delay)
        return SelectConnection(self.parameters, self.on_connection_open,
                                stop_ioloop_on_close=False)

    def print_config(self):
        to_print = [("Port", self.port),
                    ("Ssl port", self.ssl_port),
                    ("Queue", self.queue),
                    ("Exchange", self.exchange),
                    ("Heartbeat", self.heartbeat),
                    ("Host", self.host),
                    ("Use ssl", self.use_ssl),
                    ("Ssl auth", self.ssl_auth),
                    ("Vhost", self.vhost),
                    ("Redelivery timeout", self.redelivery_timeout)]
        to_print.sort()
        max_length = len(max([x[0] for x in to_print], key=len))

        self.logger.info("[AMQP-CONFIGURATION]")
        self.logger.info("##################################")
        for info in to_print:
            self.logger.info("{0:>{1}}: {2}".format(info[0], max_length,
                                                     info[1]))
        self.logger.info("##################################")

    def stop(self):
        self.logger.debug("[AMQP] Invoked stop.")
        self._closing = True
        self.close_publish_channel()
        self.close_consume_channel()
        if self._connection:
            self._connection.close()
        self.logger.info("[AMQP] Stopped.")

    def on_connection_open(self, connection):
        self.logger.info("[AMQP] Connected to %s." % self.host)
        self.add_on_connection_close_callback()
        self.open_consume_channel()
        self.open_publish_channel()

    def add_on_connection_close_callback(self):
        self._connection.add_on_close_callback(self.on_connection_closed)

    def on_connection_closed(self, connection, reply_code, reply_text):
        self._consume_channel = None
        self._publish_channel = None
        if self._closing:
            self._connection.ioloop.stop()
        else:
            self.logger.warning('Connection closed, reopening in 5 seconds')
            self._connection.add_timeout(5, self.reconnect)

    def reconnect(self):

        """Will be invoked by the IOLoop timer if the connection is
        closed. See the on_connection_closed method.

        """
        # This is the old connection IOLoop instance, stop its ioloop
        self._connection.ioloop.stop()

        # Create a new connection
        self._connection = self.connect()

        # There is now a new connection, needs a new ioloop to run
        self._connection.ioloop.start()

    ##########################
    # Consume channel handling
    ##########################
    def open_consume_channel(self):
        self.logger.debug("Opening consume channel.")
        self._connection.channel(self.on_consume_channel_open)

    def on_consume_channel_open(self, channel):
        channel.basic_qos(prefetch_count=1)
        self._consume_channel_number = channel.channel_number
        self.logger.debug("Consume channel #%d successfully opened." %
                          channel.channel_number)
        self._consume_channel = channel
        self.add_on_consume_channel_close_callback()
        self.setup_consume_channel()

    def add_on_consume_channel_close_callback(self):
        self._consume_channel.add_on_close_callback(
            self.on_consume_channel_close)

    def on_consume_channel_close(self, channel, code, text):
        self.logger.debug("Consume channel closed [%d - %s]." % (code, text))
        if code == 320:
            raise socket.error
        else:
            if self._connection:
                self._connection.add_timeout(self.retry_delay,
                                             self.open_consume_channel)

    ############################
    # Publish channel handling #
    ############################
    def open_publish_channel(self):
        self.logger.debug("Opening publish channel.")
        self._connection.channel(self.on_publish_channel_open)

    def close_publish_channel(self):
        self.logger.debug('Closing the publish channel')
        if self._publish_channel and self._publish_channel._state == 2:
            self._publish_channel.close()

    def on_publish_channel_open(self, channel):
        channel.basic_qos(prefetch_count=1)
        self._publish_channel_number = channel.channel_number
        self.logger.debug("Publish channel #%d successfully opened." %
                          channel.channel_number)
        self._publish_channel = channel
        self.add_on_publish_channel_close_callback()
        self.setup_publish_channel()

    def add_on_publish_channel_close_callback(self):
        self._publish_channel.add_on_close_callback(
            self.on_publish_channel_close)

    def on_publish_channel_close(self, channel, code, text):
        self.logger.debug("Publish channel closed [%d - %s]." % (code, text))
        if code == 320:
            raise socket.error
        else:
            if self._connection:
                self._connection.add_timeout(self.retry_delay,
                                             self.open_publish_channel)

    def setup_publish_channel(self):
        raise NotImplementedError()

    def setup_consume_channel(self):
        raise NotImplementedError()

    def close_consume_channel(self):
        self.logger.debug('Closing the consume channel')
        if self._consume_channel and self._consume_channel._state == 2:
            self._consume_channel.close()

class AmqpSynapse(Amqp):
    def __init__(self, conf, pq, tq):
        super(AmqpSynapse, self).__init__(conf)
        self.pq = pq
        self.tq = tq

    ##########################
    # Consuming
    ##########################
    def setup_consume_channel(self):
        self.add_on_cancel_callback()
        self._consumer_tag = self._consume_channel.basic_consume(
            self._on_message, self.queue)

    def add_on_cancel_callback(self):
        self._consume_channel.add_on_cancel_callback(
            self.on_consumer_cancelled)

    def on_consumer_cancelled(self, method_frame):
        self.logger.debug('Consumer was cancelled remotely, shutting down: %r',
                          method_frame)
        self._consume_channel.close()

    def on_cancelok(self, unused_frame):
        self.logger.debug('RabbitMQ acknowledged '
                         'the cancellation of the consumer')
        self.close_consume_channel()


    def stop_consuming(self):
        if self._consume_channel:
            self.logger.debug('Sending a Basic.Cancel RPC command to RabbitMQ')
            self._consume_channel.basic_cancel(
                self.on_cancelok, self._consumer_tag)

    def acknowledge_message(self, delivery_tag):
        self._consume_channel.basic_ack(delivery_tag=delivery_tag)
        self.logger.debug("[AMQP-ACK] Received message #%s acked" %
                          delivery_tag)

    def _on_message(self, channel, method_frame, header_frame, body):
        self._processing = True
        self.logger.debug("[AMQP-RECEIVE] #%s: %s" %
                          (method_frame.delivery_tag, body))
        try:
            message = IncomingMessage(body)
            headers = vars(header_frame)
            headers.update(vars(method_frame))
            task = AmqpTask(message, headers=headers)
            if not method_frame.redelivered:
                self._responses.append(method_frame.delivery_tag)
                self.tq.put(task)
            else:
                raise ValueError("Message redelivered. Won't process.")
        except ValueError as err:
            self.acknowledge_message(method_frame.delivery_tag)
            self._processing = False
            self.logger.warning(err)

    ##########################
    # Publishing
    ##########################
    def setup_publish_channel(self):
        self.start_publishing()

    def start_publishing(self):
        self._publish_channel.confirm_delivery(
            callback=self.on_confirm_delivery)
        if self._connection:
            self._connection.add_timeout(.1, self._publisher)
            self._connection.add_timeout(1, self._check_redeliveries)

    def on_confirm_delivery(self, tag):
        self.logger.debug("[AMQP-DELIVERED] #%s" % tag.method.delivery_tag)
        if tag.method.delivery_tag in self._deliveries:
            del self._deliveries[tag.method.delivery_tag]

    def _publisher(self):
        """This callback is used to check at regular interval if there's any
        message to be published to RabbitMQ.
        """
        try:
            for i in range(10):
                pt = self.pq.get(False)
                self._handle_publish(pt)
        except Empty:
            pass

        if self._connection:
            self._connection.add_timeout(.1, self._publisher)

    def _check_redeliveries(self):
        # In case we have a message to redeliver, let's wait a few seconds
        # before we actually redeliver them. This is to avoid unwanted
        # redeliveries.
        for key, value in self._deliveries.items():
            delta = datetime.now() - value['ts']
            task = value['task']
            if delta > timedelta(seconds=self.redelivery_timeout):
                self.logger.debug("[AMQP-REPLUBLISHED] #%s: %s" %
                                  (key, task.body))
                self.pq.put(task)
                del self._deliveries[key]
        if self._connection:
            self._connection.add_timeout(.1, self._check_redeliveries)

    def _handle_publish(self, message):
        """This method actually publishes the item to the broker after
        sanitizing it from unwanted informations.
        """
        publish_args = message.get()

        if (self._consume_channel and self._consume_channel._state == 2):
            delivery_tag = message.delivery_tag
            if delivery_tag in self._responses:
                self.acknowledge_message(delivery_tag)
                index = self._responses.index(delivery_tag)
                del self._responses[index]

        if (self._publish_channel and self._publish_channel._state == 2):
            self._publish_channel.basic_publish(**publish_args)

            self._message_number += 1
            self.logger.debug("[AMQP-PUBLISHED] #%s: <%s> %s" %
                             (self._message_number, message.correlation_id,
                              message.body))
        if message.redeliver:
            self._deliveries[self._message_number] = {}
            self._deliveries[self._message_number]["task"] = message
            self._deliveries[self._message_number]["ts"] = datetime.now()

        if publish_args['properties'].correlation_id is not None:
            self._processing = False
