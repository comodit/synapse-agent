import os
import uuid
import time
import pika
import json
import socket

from M2Crypto import RSA, X509, EVP, m2

from synapse.config import config
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

    signin = SigningRPC(bootstrap_opts)

    if not signin.is_connected:
        raise SynapseException('Broker unreachable.')

    csr = make_x509_request(opts['uuid'],
                            opts['csrfile'],
                            opts['keyfile'])

    resp = signin.publish_and_wait(csr)
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
class SigningRPC(object):
    def __init__(self, opts):
        self.host = opts['host']
        self.port = opts['port']
        self.vhost = opts['vhost']
        self.routing_key = opts['register_routing_key']
        self.exchange = opts['register_exchange']
        self.username = opts['username']
        self.password = opts['password']

        self.is_connected = False

        self.response = False
        credentials = pika.PlainCredentials(self.username,
                                            self.password)
        parameters = pika.ConnectionParameters(host=self.host,
                                               port=self.port,
                                               virtual_host=self.vhost,
                                               credentials=credentials)

        counter = 0
        timeout = 15
        while counter <= timeout and not self.is_connected:
            try:
                self.logger.info('Trying to bootstrap on {0}:{1} on vhost '
                                 '{2} with username [{3}] / password [{4}]'
                                 .format(self.host, self.port, self.vhost,
                                         self.username, self.password))
                self.connection = pika.BlockingConnection(parameters)
                self.channel = self.connection.channel()
                result = self.channel.queue_declare(exclusive=True,
                                                    durable=False,
                                                    auto_delete=True)
                self.callback_queue = result.method.queue
                self.channel.basic_consume(self.on_response,
                                           queue=self.callback_queue)
                self.is_connected = True
            except socket.timeout:
                self.logger.error('Connection timeout. '
                                  'Check your connection details.')
            except socket.error:
                self.logger.info('Could not reach broker. '
                                 'Retrying in 2 seconds')
                time.sleep(2)
                counter += 2

    def on_response(self, ch, method, props, body):
        self.channel.basic_ack(delivery_tag=method.delivery_tag)
        self.logger.debug(body)
        self.response = body

    def publish_and_wait(self, csr):
        self.logger.info("Publishing CSR")
        try:
            properties = pika.BasicProperties(reply_to=self.callback_queue,
                                              user_id=self.username)

            self.channel.basic_publish(exchange=self.exchange,
                                       routing_key=self.routing_key,
                                       properties=properties,
                                       body=json.dumps(csr))

            self.logger.info("Waiting for {0}s".format(TIMEOUT))

            timecount = 0
            while not self.response and timecount < TIMEOUT:
                self.connection.process_data_events()
                timecount += 1

        except (socket.timeout, NameError), err:
            msg = 'Error in signing process: {0}'.format(err)
            raise SynapseException(msg)

        self.channel.stop_consuming()
        self.connection.close()
        self.connection.disconnect()

        if not self.response:
            raise SynapseException('Did not receive response from server')

        return self.response
