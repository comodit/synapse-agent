import time
import sched

import threading

from synapse.logger import logger


@logger
class SynSched(threading.Thread):
    def __init__(self):
        self.logger.debug("Initializing the scheduler...")
        threading.Thread.__init__(self, name="SCHEDULER")

        # Start the scheduler
        self.scheduler = sched.scheduler(time.time, lambda x: time.sleep(.1))
        self.logger.debug("Scheduler successfully initialized.")

    def run(self):
        self.logger.debug("Starting the scheduler...")
        self.scheduler.run()
        self.logger.debug("Scheduler started.")

    def add_job(self, job, interval):
        self._periodic(self.scheduler, interval, job)

    def _periodic(self, scheduler, interval, action, actionargs=()):
        args = (scheduler, interval, action, actionargs)
        scheduler.enter(interval, 1, self._periodic, args)
        try:
            action(*actionargs)
        except NotImplementedError:
            pass

    def shutdown(self):
        """Shuts down the scheduler"""
        self.logger.debug("Canceling scheduled events")
        for event in self.scheduler.queue:
            self.scheduler.cancel(event)
