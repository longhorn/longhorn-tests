from recurringjob.base import Base
from recurringjob.crd import CRD
from recurringjob.rest import Rest

from strategy import LonghornOperationStrategy


class RecurringJob(Base):

    _strategy = LonghornOperationStrategy.CRD

    def __init__(self):
        if self._strategy == LonghornOperationStrategy.CRD:
            self.recurringjob = CRD()
        else:
            self.recurringjob = Rest()

    # Pushing a backup and a purge once a minute may be a little aggressive
    # Changed to every 2 minutes
    # ref: https://github.com/longhorn/longhorn/issues/7854
    def create(self,
               job_name,
               task="snapshot",
               groups=[],
               cron="*/2 * * * *",
               retain=1,
               concurrency=1,
               labels={}):
        return self.recurringjob.create(job_name, task, groups, cron, retain, concurrency, labels)

    def delete(self, job_name):
        return self.recurringjob.delete(job_name)

    def get(self, job_name):
        return self.recurringjob.get(job_name)

    def list(self, label_selector=None):
        return self.recurringjob.list(
            label_selector=label_selector
        )

    def add_to_volume(self, job_name, volume_name):
        return self.recurringjob.add_to_volume(job_name, volume_name)

    def check_jobs_work(self, volume_name):
        return self.recurringjob.check_jobs_work(volume_name)
