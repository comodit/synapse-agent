import time
import pika
import json

from Queue import Empty
from pprint import pformat
from ssl import CERT_REQUIRED

from pika.adapters import SelectConnection
from pika.adapters.select_connection import SelectPoller
from pika import PlainCredentials

from synapse.logger import logger


class ExternalCredentials(PlainCredentials):
    """ The PlainCredential class is extended to work with external rabbitmq
    auth mechanism. Here, the rabbitmq-auth-mechanism-ssl plugin than can be
    found here http://www.rabbitmq.com/plugins.html#rabbitmq_auth_mechanism_ssl

    Rabbitmq's configuration must be adapted as follow:
    [
    {rabbit, [
     {auth_mechanisms, ['EXTERNAL', 'PLAIN']},
     {ssl_listeners, [5671]},
     {ssl_options, [{cacertfile,"/etc/rabbitmq/testca/cacert.pem"},
                    {certfile,"/etc/rabbitmq/server/cert.pem"},
                    {keyfile,"/etc/rabbitmq/server/key.pem"},
                    {verify,verify_peer},
                    {fail_if_no_peer_cert,true}]}
    ]}
    ].
    """
    TYPE = 'EXTERNAL'

    def __init__(self):
        self.erase_on_connect = False

    def response_for(self, start):

        if ExternalCredentials.TYPE not in start.mechanisms.split():
            return None, None
        return ExternalCredentials.TYPE, ""

    def erase_credentials(self):
        pass

# As mentioned in pika's PlainCredentials class, we need to append the new
# authentication mechanism to VALID_TYPES
pika.credentials.VALID_TYPES.append(ExternalCredentials)


class AmqpError(Exception):
    pass


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
        self.retry_timeout = conf['retry_timeout']
        self.ssl_auth = conf['ssl_auth']
        self.use_ssl = conf['use_ssl']
        self.username = conf['username']
        self.vhost = conf['vhost']

        # Connection and channel initialization
        self.connection = None
        self.channel = None

        # Plain credentials
        credentials = PlainCredentials(self.username, self.password)
        pika_options = {'host': self.host,
                        'port': self.port,
                        'virtual_host': self.vhost,
                        'credentials': credentials}

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
            pika_options['heartbeat'] = self.heartbeat

        self.parameters = None

        try:
            self.parameters = pika.ConnectionParameters(**pika_options)
        except TypeError as err:
            self.logger.debug(err)
            # Let's be compatible with original pika version (no integer for
            # heartbeats and no ssl.
            self.logger.warning("Wrong pika lib version, won't use ssl.")
            pika_options['heartbeat'] = True
            if self.use_ssl:
                self.use_ssl = False
                pika_options['port'] = self.port
                del pika_options['ssl']
                if self.ssl_auth:
                    self.ssl_auth = False
                    del pika_options['ssl_options']

            self.parameters = pika.ConnectionParameters(**pika_options)

    def connect(self):
        SelectPoller.TIMEOUT = .1
        self.connection = SelectConnection(self.parameters, self.on_connected)
        self.connection.ioloop.start()

    def close(self, amqperror=False):
        if (self.connection and not self.connection.closing
            and not self.connection.closed):

            self.logger.debug("Closing connection")
            self.connection.close()
            #self.connection.ioloop.start()

    def on_remote_close(self, code, text):
        self.logger.debug("Remote channel close, code %d" % code)
        time.sleep(2)
        if code != 200:
            self.close()
            raise AmqpError(text)

    def on_connection_closed(self, frame):
        self.connection.ioloop.stop()

    def on_connected(self, connection):
        self.connection = connection
        self.connection.add_on_close_callback(self.on_connection_closed)
        self.connection.channel(self.on_channel_open)


class AmqpAdmin(Amqp):
    def on_channel_open(self, channel):
        """Callback for when the channel is opened. Once the channel is opened,
        it's time to add a callback to check the publish queue and a callback
        for channel errors.
        """

        self.channel = channel
        self.channel.add_on_close_callback(self.on_remote_close)
        self.channel.queue_declare(queue=self.queue, durable=True,
                                   exclusive=False, auto_delete=False,
                                   callback=self.on_queue_declared)

    def on_queue_declared(self, frame):
        self.channel.exchange_declare(exchange=self.status_exchange,
                                      durable=True,
                                      type='fanout',
                                      callback=self.on_exchange_declared)

    def on_exchange_declared(self, frame):
        self.channel.exchange_declare(exchange=self.exchange, durable=True,
                                      type='fanout',
                                      callback=self.on_st_exchange_declared)

    def on_st_exchange_declared(self, frame):
        self.channel.queue_bind(exchange=self.exchange, queue=self.queue,
                                callback=self.on_queue_bound)

    def on_queue_bound(self, frame):
        self.close()

    def on_remote_close(self, code, text):
        if code != 200:
            self.logger.warning(text)
            self.connection.add_timeout(.25, self.close)


class AmqpSynapse(Amqp):
    def __init__(self, conf, publish_queue=None, tasks_queue=None):
        super(AmqpSynapse, self).__init__(conf)
        self.publish_queue = publish_queue
        self.tasks_queue = tasks_queue

    def on_channel_open(self, channel):
        """Callback for when the channel is opened. Once the channel is opened,
        it's time to add a callback to check the publish queue and a callback
        for channel errors.
        """

        msg = "Connected to RabbitMQ on %s" % self.host
        if self.use_ssl:
            msg += ":%s with SSL" % self.ssl_port
        else:
            msg += ":%s" % self.port

        self.logger.info(msg)

        self.channel = channel
        self.channel.add_on_close_callback(self.on_remote_close)
        self.channel.basic_consume(consumer_callback=self.handle_delivery,
                                   queue=self.queue)
        self.logger.debug("Consuming on queue %s" % self.queue)
        self.publish_timeout_id = self.connection.add_timeout(
            1, lambda: self._publisher())

    def handle_delivery(self, channel, method_frame, header_frame, body):
        self.channel.basic_ack(delivery_tag=method_frame.delivery_tag)
        self.logger.debug("Header Frame: %s" % header_frame)
        self.logger.debug("Method Frame: %s" % method_frame)
        self.logger.debug("Body: %s" % body)

        if not method_frame.redelivered:
            self.tasks_queue.put((vars(header_frame), body))
        else:
            self.logger.warning("This message was redelivered. Won't process.")


    def _publisher(self):
        """This callback is used to check at regular interval if there's any
        message to be published to RabbitMQ.
        """

        if not self.connection.close or not self.connection.closing:
            try:
                for i in range(5):
                    headers, item = self.publish_queue.get(False)
                    self._handle_publish(headers, item)

            except Empty:
                pass

        self.connection.add_timeout(.1, lambda: self._publisher())

    def _handle_publish(self, headers={}, item={}):
        """This method actually publishes the item to the broker after
        sanitizing it from unwanted informations.
        """

        exchange = ''
        reply_to = ''
        props = {}
        try:
            if 'headers' in headers:
                exchange = headers['headers'].get('reply_exchange', '')

            reply_to = headers.get('reply_to', headers.get('routing_key', ''))

            props = {
                'correlation_id': headers.get('correlation_id'),
                'user_id': self.username or None
            }
        except Exception as err:
            self.logger.error(err)

        properties = pika.BasicProperties(**props)

        self.logger.debug('Publishing into exchange [%s] with routing '
                          'key [%s]' % (exchange, reply_to))
        self.logger.debug('Message:\n' + pformat(item, width=80))

        if exchange or reply_to:
            self.channel.basic_publish(exchange=exchange,
                                       routing_key=reply_to,
                                       properties=properties,
                                       body=json.dumps(item))
        else:
            self.logger.warning("This message has no information about how "
                                "to be routed to RabbitMQ. Won't publish.")
