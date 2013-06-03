import os

from io import StringIO
from ConfigParser import RawConfigParser

from synapse.syncmd import exec_cmd
from synapse.config import config
from synapse.logger import logger
from synapse.scheduler import SynSched
from synapse.resources.resources import ResourcesController
from synapse.task import OutgoingMessage, AmqpTask
from synapse import compare


@logger
class AlertsController(object):
    def __init__(self, locator, scheduler, publish_queue):
        self.path = self._configure()
        self.plugins = {}
        self._load_configs()
        self.publish_queue = publish_queue
        self.locator = locator
        self.scheduler = scheduler

        self.alerts = []

    def start(self):
        self._add_alerts()
        self.scheduler.add_job(self._reload, 30)

    def _configure(self):
        config_path = os.path.join(config.paths['config_path'], 'alerts.d')
        if not os.path.exists(config_path):
            os.makedirs(config_path)
        return config_path

    def _reload(self):
        self._load_configs()
        self._add_alerts()

    def _load_configs(self):
        for conf_file in os.listdir(self.path):
            if not conf_file.endswith('.conf'):
                continue
            full_path = os.path.join(self.path, conf_file)
            conf = RawConfigParser()
            conf.read(full_path)
            for section in conf.sections():
                self.plugins[section] = []
                items = dict(conf.items(section))
                for key, value in items.iteritems():
                    task = {'method': key,
                            'value': value,
                            'scheduled': False}
                    self.plugins[section].append(task)

    def _add_alerts(self):
        for resource, tasks in self.plugins.iteritems():
            instance = self.locator.get_instance(resource)
            for task in tasks:
                if task['scheduled']:
                    continue
                method_ref = getattr(instance, task['method'])
                parsed_params = self._parse_parameters(task['value'])
                interval = int(parsed_params[0])
                compare_method = parsed_params[1]
                threshold = parsed_params[2]
                actionargs = (method_ref, compare_method, threshold)
                self.scheduler.update_job(self.alert, int(interval),
                                          actionargs=actionargs)
                task['scheduled'] = True

    def _parse_parameters(self, parameters):
        return parameters.split(',') + [None] * (4 - len(parameters))

    def alert(self, sensor, compare_method, threshold):
        value = sensor()

        if compare_method is not None and threshold is not None:
            result = getattr(compare, compare_method)(value, threshold)
            alert = {
                'property': sensor.__name__,
                'output': value,
                'level': 'warning',
                'threshold': threshold,
                'compare_method': compare_method,
            }

            if result and not self._alert_sent(alert):
                self._add_alert(alert)
                self._publish(sensor, alert)

            elif not result and self._alert_sent(alert):
                self._remove_alert(alert)
                alert['level'] = 'normal'
                self._publish(sensor, alert)

    def _publish(self, sensor, alert):
        msg = {
            'collection': sensor.__self__.__class__.__resource__,
            'msg_type': 'alert',
            'status': alert
        }

        self.publish_queue.put(AmqpTask(OutgoingMessage(**msg)))

    def _alert_sent(self, alert):
        for al in self.alerts:
            if alert['property'] == al['property']:
                return True
        return False

    def _add_alert(self, alert):
        self.alerts.append(alert)

    def _remove_alert(self, alert):
        for al in self.alerts:
            if alert['property'] == al['property']:
                self.alerts.remove(al)

    def close(self):
        super(AlertsController, self).close()
        self.logger.debug("Shutting down alerts scheduler")
        self.scheduler.shutdown()

