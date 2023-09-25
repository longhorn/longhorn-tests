from recurring_job.base import Base
from recurring_job.crd import CRD
from recurring_job.rest import Rest
from strategy import LonghornOperationStrategy


class RecurringJob(Base):

    _strategy = LonghornOperationStrategy.CRD

    def __init__(self):
        if self._strategy == LonghornOperationStrategy.CRD:
            self.recurring_job = CRD()
        else:
            self.recurring_job = Rest()

    def create(self,
               job_name,
               task="snapshot",
               groups=[],
               cron="* * * * *",
               retain=1,
               concurrency=1,
               labels={}):
        return self.recurring_job.create(job_name, task, groups, cron, retain, concurrency, labels)

    def delete(self, job_name, volume_name):
        return self.recurring_job.delete(job_name, volume_name)

    def get(self, job_name):
        return self.recurring_job.get(job_name)

    def add_to_volume(self, job_name, volume_name):
        return self.recurring_job.add_to_volume(job_name, volume_name)

    def check_jobs_work(self, volume_name):
        return self.recurring_job.check_jobs_work(volume_name)

    def cleanup(self, volume_names):
        return self.recurring_job.cleanup(volume_names)