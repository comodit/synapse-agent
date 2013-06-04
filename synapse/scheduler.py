import time
import sched

import threading

from synapse.config import config
from synapse.logger import logger


@logger
class SynSched(threading.Thread):
    def __init__(self):
        self.logger.debug("Initializing the scheduler...")
        threading.Thread.__init__(self, name="SCHEDULER")

        # Start the scheduler
        self.scheduler = sched.scheduler(time.time, lambda x: time.sleep(.1))

    def run(self):
        self.scheduler.run()
        self.logger.debug("Scheduler started...")

    def add_job(self, job, interval, actionargs=()):
        self.logger.debug("Adding job '%s' to scheduler every %d seconds" %
                          (job, interval))
        self._periodic(self.scheduler, interval, job, actionargs=actionargs)

    def update_job(self, job, interval, actionargs=()):
        job_name = actionargs[0].__name__
        existing_job = self.get_job(job_name)
        if existing_job is None:
            self.add_job(job, interval, actionargs)
        elif (interval != existing_job.argument[1] or
              actionargs != existing_job.argument[3]):
                self.scheduler.cancel(existing_job)
                self.add_job(job, interval, actionargs)

    def get_job(self, job_name):
        job = None
        for event in self.scheduler.queue:
            if len(event.argument[3]):
                if job_name == event.argument[3][0].__name__:
                    job = event
            else:
                if job_name == event.argument[2].__name__:
                    job = event

        return job

    def _periodic(self, scheduler, interval, action, actionargs=()):
        args = (scheduler, interval, action, actionargs)
        scheduler.enter(interval, 1, self._periodic, args)
        try:
            action(*actionargs)
        except NotImplementedError:
            pass

    def shutdown(self):
        """Shuts down the scheduler."""
        self.logger.debug("Canceling scheduled events")
        for event in self.scheduler.queue:
            self.scheduler.cancel(event)
