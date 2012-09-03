import os
import pickle
from pickle import PicklingError, PickleError

from synapse.synapse_exceptions import SynapseException
from synapse.config import config
from synapse.logger import logger


@logger
class Persistence(object):
    def __init__(self):
        opts = config.controller
        self.path = opts['persistence_path']

        if not os.path.exists(self.path):
            raise Exception('Persistence path does not exist.')

        file_list = os.listdir(self.path)
        for fname in file_list:
            if fname.endswith('.pkl'):
                try:
                    collection = fname[:-4]
                    path = os.path.join(self.path, fname)
                    with open(path, 'rb') as fd:
                        setattr(self, collection, pickle.load(fd))
                    self.logger.debug('Loaded persisted <{0}>'
                                      ' collection'.format(collection))
                except (PickleError, PicklingError), err:
                    raise SynapseException(err)
                except (IOError, EOFError):
                    pass

    def persist(self, resource, update_alert=False):
        if resource.get('error', '') != '':
            return None

        collection = resource['collection']
        resource_id = resource['resource_id']
        try:
            data = getattr(self, collection)
            indexes = [i for i, x in enumerate(data)
                       if x['resource_id'] == resource_id]
            if len(indexes):
                if len(indexes) > 1:
                    data = list(set(data))
                data[indexes[0]].update(resource)
                if not update_alert:
                    try:
                        del data[indexes[0]]['status']['last_alert']
                    except KeyError:
                        pass
            elif len(indexes) == 0:
                data.append(resource)

        except AttributeError:
            setattr(self, collection, [])
            getattr(self, collection).append(resource)

        finally:
            path = os.path.join(self.path, collection + '.pkl')
            with open(path, 'wb') as fd:
                os.chmod(path, int('0600', 8))
                pickle.dump(getattr(self, collection), fd)
            self.logger.debug('%s status has been persisted.' % collection)

    def unpersist(self, resource):
        if resource.get('error', '') != '':
            return None

        collection = resource['collection']
        resource_id = resource['resource_id']
        try:
            data = getattr(self, collection)
            indexes = [i for i, x in enumerate(data)
                       if x['resource_id'] == resource_id]
            for i in indexes:
                del data[i]

        except AttributeError:
            setattr(self, collection, [])
            getattr(self, collection).append(resource)

        finally:
            path = os.path.join(self.path, collection + '.pkl')
            with open(path, 'wb') as fd:
                os.chmod(path, int('0600', 8))
                pickle.dump(getattr(self, collection), fd)
            self.logger.debug('%s status has been unpersisted.' % collection)
