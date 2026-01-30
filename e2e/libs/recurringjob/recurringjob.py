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
               labels={},
               parameters=None):
        return self.recurringjob.create(job_name, task, groups, cron, retain, concurrency, labels, parameters)

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

    def check_recurringjob_work_for_volume(self, job_name, job_task, volume_name):
        self.recurringjob.check_recurringjob_work_for_volume(job_name, job_task, volume_name)

    def wait_for_systembackup_state(self, job_name, expected_state):
        return self.recurringjob.wait_for_systembackup_state(job_name, expected_state)

    def assert_recurringjob_created_backup_for_volume(self, volume_name, job_name, retry_count=-1):
        return self.recurringjob.assert_volume_backup_created(volume_name, job_name, retry_count=retry_count)

    def wait_for_pod_completion_without_error(self, job_name):
        return self.recurringjob.wait_for_pod_completion_without_error(job_name)

    def wait_for_recurringjob_pod_completion(self, job_name):
        return self.recurringjob.wait_for_recurringjob_pod_completion(job_name)

    def check_recurringjob_concurrency(self, job_name, concurrency):
        return self.recurringjob.check_recurringjob_concurrency(job_name, concurrency)

    def update_recurringjob(self, job_name, groups, cron, concurrency, labels, parameters):
        self.recurringjob.update_recurringjob(job_name, groups, cron, concurrency, labels, parameters)
