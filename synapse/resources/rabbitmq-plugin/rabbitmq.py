import json
import urllib2, base64
from synapse.logger import logger
from synapse.resources.resources import ResourcesController


@logger
class RabbitmqController(ResourcesController):

    __resource__ = "rabbitmq"

    def file_descriptors(self):
        username = 'guest'
        password = 'guest'
        request = urllib2.Request("http://localhost:55672/api/nodes")
        base64string = base64.encodestring('%s:%s' % (username, password)).replace('\n', '')
        request.add_header("Authorization", "Basic %s" % base64string)
        try:
            result = urllib2.urlopen(request)
            return json.loads(result.read())[0]['fd_used']
        except urllib2.URLError as err:
            return 0
