import time
import json
import urllib2

from pprint import pformat

from synapse.config import config
from synapse.controller import Controller
from synapse.logger import logger
from synapse.synapse_exceptions import ResourceException


@logger
class ResourceFile:
    def __init__(self, transport):
        opts = config.resourcefile
        self.transport = transport
        self.url = opts['url']
        self.path = opts['path']
        self.timeout = opts['timeout']
        self.done = False

    def fetch(self):
        counter = 0
        while counter <= self.timeout and not self.done:
            try:
                self.dispatch(self.transport)
                self.done = True
                self.logger.info("Done processing.")
            except urllib2.HTTPError, err:
                #code = err.code
                self.logger.error("File not found: %s" % err)
            except IOError, err:
                # Connection error (socket)
                self.logger.error("IOError: %s" % err)
            except Exception, err:
                self.logger.error("SynapseException: %s" % err)
                self.done = True
            finally:
                if not self.done:
                    self.logger.info('Retrying in 2 seconds. '
                            '{0} seconds left'.format(self.timeout - counter))
                    time.sleep(2)
                    counter += 2

    def dispatch(self, transport):
        tasks = {'http': self._get_http, 'file': self._get_fs}[transport]()

        for task in tasks:
            response = ''
            try:
                self.logger.info("Sending task:\n{0}\n".format(pformat(task)))
                response = Controller().call_method('', task, check_perm=False)
            except ResourceException, error:
                response = error

            self.logger.info("Response:\n{0}\n".format(pformat(response)))

        return True

    def _get_http(self):
        self.logger.info('Trying to open url %s' % self.url)
        webfile = urllib2.urlopen(self.url)
        try:
            tasks = json.loads(webfile.read())
            self.logger.info('Found %d task(s), processing...' % len(tasks))
        except ValueError, err:
            raise Exception('Error while loading json: {0}'.format(err))
        finally:
            webfile.close()
        return tasks

    def _get_fs(self):
        self.logger.info('Trying to open file %s' % self.path)
        with open(self.path, 'r') as fd:
            try:
                tasks = json.load(fd)
                self.logger.info('Found %d task(s)' % len(tasks))
            except ValueError, err:
                raise Exception('Error while loading json: {0}'.format(err))
        return tasks or []
