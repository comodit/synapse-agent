import json
import urllib2, base64
from synapse.logger import logger
from synapse.resources.resources import ResourcesController


@logger
class RabbitmqController(ResourcesController):

    __resource__ = "rabbitmq"

    def read(self, res_id=None, attributes={}):
        sensors = attributes.keys()

        status = {}
        if 'file_descriptors' in sensors:
            params = attributes['file_descriptors']
            status['file_descriptors'] = self.file_descriptors(params)

        return status

    def file_descriptors(self, parameters={}):
        username = parameters.get('username', 'guest')
        password = parameters.get('password', 'guest')
        url = parameters.get('url', 'http://localhost:55672/api/nodes')
        request = urllib2.Request(url)
        base64string = base64.encodestring('%s:%s' % (username, password)).replace('\n', '')
        request.add_header("Authorization", "Basic %s" % base64string)
        try:
            result = urllib2.urlopen(request)
            return json.loads(result.read())[0]['fd_used']
        except urllib2.URLError as err:
            return 0
