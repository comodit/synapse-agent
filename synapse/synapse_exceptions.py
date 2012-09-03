from synapse.config import config


class ResourceException(Exception):
    pass


class MethodNotAllowedException(Exception):
    def __init__(self, value):
        opts = config.rabbitmq
        self.error = {}
        self.error['uuid'] = opts['uuid']
        self.error['error'] = value
        self.error['status'] = {}

    def __str__(self):
        return repr(self.error)


class SynapseException(Exception):
    def __init__(self, value=''):
        opts = config.rabbitmq
        self.value = value
        self.error = {}
        self.error['uuid'] = opts['uuid']
        self.error['error'] = value
        self.error['status'] = {}

    def __str__(self):
        return repr(self.error)
