from synapse.config import config


def check(uuids):
    return config.rabbitmq['uuid'] in uuids
