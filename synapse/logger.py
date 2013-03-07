import copy
import logging
import inspect
import logging.config

from synapse.config import config

LEVELS = ('FATAL', 'ERROR', 'WARNING', 'INFO', 'DEBUG', 'CRITICAL')


def logger(obj):
    if inspect.isclass(obj):
        setattr(obj,
                'logger',
                logging.getLogger('synapse.{0}'.format(obj.__name__)))
        return obj
    else:
        try:
            modulename = obj.split('.')[-1]
            return logging.getLogger('synapse.{0}'.format(modulename))
        except (AttributeError, IndexError):
            return logging.getLogger('synapse')


def setup_logging(logconf):
    # Get log level from config file
    logging.config.fileConfig(logconf['logger_conf'])


class SynapseFileHandler(logging.FileHandler):
    def __init__(self, mode):
        path = config.log['path']
        logging.FileHandler.__init__(self, path, mode)


class ConsoleUnixColoredHandler(logging.StreamHandler):
    BLACK, RED, GREEN, YELLOW, BLUE, MAGENTA, CYAN, WHITE = range(8)
    COLORS = {
        'FATAL': RED,
        'CRITICAL': RED,
        'ERROR': RED,
        'WARNING': YELLOW,
        'INFO': GREEN,
        'DEBUG': CYAN,
    }

    def emit(self, r):
        # Need to make a actual copy of the record to prevent altering
        # the message for other loggers.
        record = copy.copy(r)
        levelname = record.levelname

        # Configures the current colors to use.
        color = self.COLORS[record.levelname]

        # Colories the levelname of each log message
        record.levelname = self._get_fg_color(color) + str(levelname) + \
            self._reset()
        logging.StreamHandler.emit(self, record)

    def _get_fg_color(self, color):
        return '\x1B[1;3%sm' % color

    def _reset(self):
        return '\x1B[1;%sm' % self.BLACK
