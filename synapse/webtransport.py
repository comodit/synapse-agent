import web
import sys
import json
from synapse.synapse_exceptions import SynapseException

from synapse.log import log


class WebTransport(object):
    def __init__(self, controller=None):
        globals()['ctrl'] = controller
        log.debug("Initialized controller")
        try:
            self.urls = ("/(.*)", "Restapi")
            sys.argv[1:] = ['8888']
        except ValueError, err:
            raise SynapseException('Wrong port (%s)' % err)

    def start(self):
        log.debug("Starting REST API")
        app = web.application(self.urls, globals())
        app.run()


class Restapi:
    def GET(self, path):
        return self.process_request(path, 'read')

    def POST(self, path):
        return self.process_request(path, 'create')

    def PUT(self, path):
        return self.process_request(path, 'udpate')

    def DELETE(self, path):
        return self.process_request(path, 'delete')

    def process_request(self, path, action):
        msg = {}
        try:
            path.lstrip('/')
            path_parts = path.split('/')
            msg['action'] = action
            msg['collection'] = path_parts[0]
            if len(path_parts) > 1:
                id = path_parts[1]
                msg['id'] = id

            if len(web.data()):
                msg['attributes'] = json.loads(web.data())
            log.debug('REST Msg: %s' % msg)

        except IndexError, err:
            return err
        except ValueError, err:
            return err
        response = globals()['ctrl'].call_method(msg)

        return response
