import os
from io import StringIO


from ConfigParser import RawConfigParser
from synapse.syncmd import exec_cmd
from synapse.config import config
from synapse.logger import logger
from synapse.scheduler import SynSched
from synapse.resources.resources import ResourcesController
from synapse.task import OutgoingMessage


@logger
class NagiosPluginsController(ResourcesController):

    __resource__ = "nagios"

    def __init__(self, module):
        super(NagiosPluginsController, self).__init__(module)
        self.path = self._configure()
        self.plugins = {}
        self._load_configs()
        self.scheduler = SynSched()
        self.scheduler.start()
        self._load_jobs()
        self.scheduler.add_job(self._reload, 30)

    def read(self, res_id=None, attributes=None):
        sensors = attributes.keys()
        status = {}
        for sensor in sensors:
            if sensor in self.plugins.keys():
                status[sensor] = exec_cmd(self.plugins[sensor]['command'])

        return status

    def _configure(self):
        config_path = os.path.join(config.paths['config_path'], 'nagios.d')
        if not os.path.exists(config_path):
            os.makedirs(config_path)
        return config_path

    def _reload(self):
        self._load_configs()
        self._load_jobs()

    def _load_configs(self):
        for conf_file in os.listdir(self.path):
            if not conf_file.endswith('.conf'):
                continue
            full_path = os.path.join(self.path, conf_file)
            conf = RawConfigParser()
            conf.read(full_path)
            for section in conf.sections():
                if section not in self.plugins:
                    self.plugins[section] = dict(conf.items(section))
                    self.plugins[section]['scheduled'] = False

    def _load_jobs(self):
        for key, value in self.plugins.iteritems():
            if value['scheduled']:
                continue

            try:
                interval = int(value['interval'])
                command = value['command']
                if os.path.exists(command.split()[0]):
                    self.scheduler.add_job(self._execute,
                                           interval,
                                           actionargs=(key, command))
                    self.plugins[key]['scheduled'] = True
                else:
                    self.logger.warning("%s doesn't exist" % command)

            except ValueError:
                self.logger.warning("Interval value for %s must be an int" %
                                    key)
            except KeyError as err:
                self.logger.warning("Error when parsing %s (%s)" %
                                    (self.path, key))

    def _execute(self, name, cmd):
        result = exec_cmd(cmd)
        if result['returncode'] != 0:
            result['name'] = name
            msg = OutgoingMessage(collection=self.__resource__, status=result,
                                  msg_type='alert')
            self.publish(msg)

    def close(self):
        super(NagiosPluginsController, self).close()
        self.logger.debug("Shutting down nagios scheduler")
        self.scheduler.shutdown()
