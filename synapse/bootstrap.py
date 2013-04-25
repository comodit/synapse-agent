
import os
import uuid
import time
import pika
import json
import socket
from Queue import Queue

from M2Crypto import RSA, X509, EVP, m2

from synapse.config import config
from synapse.amqp import Amqp
from synapse.logger import logger
from synapse_exceptions import SynapseException


TIMEOUT = 5

log = logger(__name__)


def bootstrap(options):

    bootstrap_opts = get_bootstrap_config()

    if options.force:
        bootstrap_opts['register'] = True
        pem_list = ('cert', 'cacert', 'key', 'csr')
        for pem in pem_list:
            try:
                os.remove(config.paths[pem])
            except (IOError, OSError):
                pass

    if not bootstrap_opts['register']:
        return

    opts = config.rabbitmq

    if not bootstrap_opts['uuid']:
        if not opts['uuid']:
            bootstrap_opts['uuid'] = str(uuid.uuid4())
        else:
            bootstrap_opts['uuid'] = opts['uuid']
    else:
        opts['uuid'] = bootstrap_opts['uuid']

    # Iterate over pem files paths. If at least one of them exists, don't
    # continue and raise an exception.
    exclude = ('csrfile', 'certfile', 'keyfile', 'cacertfile')
    if True in [os.path.exists(pem) for pem in exclude]:
        raise SynapseException("A pem file already exists. "
                               "Use --force with care to regenerate keys/csr.")

    csr = make_x509_request(opts['uuid'],
                            opts['csrfile'],
                            opts['keyfile'])

    response_queue = Queue()
    amqp = AmqpBootstrap(config.rabbitmq,
                         bootstrap_opts,
                         csr,
                         response_queue,
                         timeout=TIMEOUT).run()
    resp = {}

    resp = response_queue.get(True, TIMEOUT)

    response = json.loads(resp)

    if 'cert' in response:
        log.debug("Received certificate: %s" % response['cert'])
        save_cert(response, opts['certfile'], opts['cacertfile'])

        config.bootstrap['register'] = False
        config.bootstrap['uuid'] = bootstrap_opts['uuid']
        config.rabbitmq['username'] = bootstrap_opts['uuid']
        config.rabbitmq['uuid'] = bootstrap_opts['uuid']
        config.rabbitmq['host'] = bootstrap_opts['host']
        config.rabbitmq['vhost'] = bootstrap_opts['vhost']
        config.rabbitmq['use_ssl'] = True
        config.rabbitmq['ssl_auth'] = True

    else:
        raise Exception(response.get('error', 'Unknown error'))


def get_bootstrap_config():
    conf = {
        'register': False,
        'host': 'localhost',
        'vhost': '/',
        'port': '5672',
        'register_exchange': 'register',
        'register_routing_key': '',
        'username': 'guest',
        'password': 'guest',
        'uuid': '',
        }

    conf.update(config.conf.get('bootstrap', {}))

    conf['register'] = config.sanitize_true_false(conf['register'])
    conf['port'] = config.sanitize_int(conf['port'])

    return conf


def generateRSAKey():
    #RSA_F4 = 65637 -> PubExponent
    return RSA.gen_key(2048, m2.RSA_F4)


def makePKey(key):
    pkey = EVP.PKey()
    pkey.assign_rsa(key)
    return pkey


def make_x509_request(uuid, csrpath, keypath):
    rsa = generateRSAKey()
    pkey = makePKey(rsa)
    req = X509.Request()
    req.set_pubkey(pkey)
    name = X509.X509_Name()
    name.CN = uuid
    req.set_subject_name(name)
    req.sign(pkey, 'sha1')
    req.save(csrpath)
    rsa.save_key(keypath, cipher=None)
    os.chmod(keypath, 0640)
    message = {}
    message['uuid'] = name.CN
    with open(csrpath, 'r') as fd:
        message['csr'] = fd.read()
    return message


def save_cert(msg, certpath, cacertpath):
    if not isinstance(msg, dict):
        save_cert.log.error('Bad response format')
    with open(certpath, 'w') as fd:
        cert = msg.get('cert', '')
        fd.write(cert)
    with open(cacertpath, 'w') as fd:
        cacert = msg.get('cacert', '')
        fd.write(cacert)

@logger
class AmqpBootstrap(Amqp):
    def __init__(self, config, options, csr, response_queue, timeout=5):
        self.host = config['host'] = options['host']
        self.port = config['port'] = options['port']
        self.vhost = config['vhost'] = options['vhost']
        self.username = config['username'] = options['username']
        self.password = config['password'] = options['password']
        super(AmqpBootstrap, self).__init__(config)
        self.routing_key = options['register_routing_key']
        self.exchange = options['register_exchange']
        self.csr = csr
        self.timeout = timeout

        self.queue = ''

        self._consumer_tag = None
        self.response_queue = response_queue

    def setup_consume_channel(self):
        self._consume_channel.queue_declare(self.on_queue_declareok,
                                            durable=False,
                                            exclusive=True,
                                            auto_delete=True)

    def on_queue_declareok(self, method_frame):
        self.logger.info("Waiting a response for %d seconds", self.timeout)
        self._connection.add_timeout(self.timeout, self.stop)
        self.queue = method_frame.method.queue
        self.start_consuming()

    def start_consuming(self):
        self.add_on_cancel_callback()
        self._consumer_tag = self._consume_channel.basic_consume(
            self.on_message, self.queue)
        self.publish()

    def add_on_cancel_callback(self):
        self._consume_channel.add_on_cancel_callback(
            self.on_consumer_cancelled)

    def on_consumer_cancelled(self, method_frame):
        self.logger.info('Consumer was cancelled remotely, shutting down: %r',
                    method_frame)
        if self._consume_channel:
            self._consume_channel.close()

    def stop_consuming(self):
        if self._consume_channel:
            self.logger.debug('Sending a Basic.Cancel RPC command to RabbitMQ')
            self._consume_channel.basic_cancel(self.on_cancelok,
                                               self._consumer_tag)
    def on_cancelok(self, unused_frame):
        self.logger.debug('RabbitMQ acknowledged the cancellation '
                          'of the consumer')
        self.close_channel()

    def close_channel(self):
        """Call to close the channel with RabbitMQ cleanly by issuing the
        Channel.Close RPC command.

        """
        self.logger.debug('Closing the channel')
        self._consume_channel.close()

    def on_message(self, channel, basic_deliver, properties, body):
        self.logger.info('Received message # %s from %s: %s',
                    basic_deliver.delivery_tag, properties.app_id, body)
        self.acknowledge_message(basic_deliver.delivery_tag)
        self.response_queue.put(body)
        self.stop_consuming()
        self.stop()

    def acknowledge_message(self, delivery_tag):
        self._consume_channel.basic_ack(delivery_tag)

    def setup_publish_channel(self):
        """ Do nothing here. We want to be sure we're already consuming before
        publishing anything. See self.publish() in start_consuming method.
        """
        pass

    def publish(self):
        self._publish_channel.confirm_delivery(
            callback=self.on_confirm_delivery)

        properties = pika.BasicProperties(reply_to=self.queue,
                                          user_id=self.username)

        self._publish_channel.basic_publish(exchange=self.exchange,
                                            routing_key=self.routing_key,
                                            properties=properties,
                                            body=json.dumps(self.csr))

    def on_confirm_delivery(self, tag):
        self.logger.debug("[AMQP-DELIVERED] #%s" % tag.method.delivery_tag)
