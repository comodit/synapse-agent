import os, stat
import pickle
from pickle import PicklingError, PickleError
from operator import itemgetter

from synapse.synapse_exceptions import SynapseException
from synapse.config import config
from synapse.logger import logger


@logger
class StatesManager(object):
    def __init__(self, resource_name):
        self.resource_name = resource_name

        # Get folder where states are persisted
        folder = config.controller['persistence_path']

        # If folder does not exist, raise exception
        if not os.path.exists(folder):
            raise Exception('Persistence folder does not exist.')

        # Filename for this resource state manager
        self.path = os.path.join(folder, resource_name + '.pkl')

        # Load states in memory
        self.states = self._load_from_file(self.path)

    def _load_from_file(self, path):
        states = []
        try:
            if os.path.exists(path):
                with open(path, 'rb') as fd:
                    states = pickle.load(fd)
        except (PickleError, PicklingError), err:
            raise SynapseException(err)
        except (IOError, EOFError):
            pass

        self.logger.debug("Loading %d persisted resources states from %s" %
                          (len(states), path))

        return states

    def persist(self):
        try:
            with open(self.path, 'wb') as fd:
                os.chmod(self.path, stat.S_IREAD | stat.S_IWRITE)
                pickle.dump(self.states, fd)
        except IOError as err:
            self.logger.error(err)

    def shutdown(self):
        for state in self.states:
            if 'last_alert' in state:
                state['last_alert'] = None
        self.persist()

    def save_state(self, res_id, state, monitor):
        if monitor is False:
            self._remove_state(res_id)

        else:
            item = {
                'uuid': config.rabbitmq['uuid'],
                'resource_id': res_id,
                'collection': self.resource_name,
                'status': state,
                'compliant': True,
                'back_to_compliance': False
            }

            self._update_state(item)
        self.persist()

    def _update_state(self, state):
        index = self._get_index(state['resource_id'])
        if index != -1:
            state['back_to_compliance'] = not self.states[index]['compliant']
            self.states[index].update(state)
        else:
            self.states.append(state)

    def _remove_state(self, res_id):
        index = self._get_index(res_id)
        if index != -1:
            del self.states[index]

    def _get_index(self, res_id):
        try:
            return map(itemgetter('resource_id'), self.states).index(res_id)
        except ValueError:
            return -1

    def _get_state(self, res_id):
        index = self._get_index(res_id)
        return self.states[index] if index != -1 else {}

