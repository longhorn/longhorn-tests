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

    def create(self,
               job_name,
               task="snapshot",
               groups=[],
               cron="* * * * *",
               retain=1,
               concurrency=1,
               labels={}):
        return self.recurringjob.create(job_name, task, groups, cron, retain, concurrency, labels)

    def delete(self, job_name, volume_name):
        return self.recurringjob.delete(job_name, volume_name)

    def get(self, job_name):
        return self.recurringjob.get(job_name)

    def add_to_volume(self, job_name, volume_name):
        return self.recurringjob.add_to_volume(job_name, volume_name)

    def check_jobs_work(self, volume_name):
        return self.recurringjob.check_jobs_work(volume_name)

    def cleanup(self, volume_names):
        return self.recurringjob.cleanup(volume_names)
