import ast
import time

from recurringjob import RecurringJob

from utility.constant import LABEL_TEST
from utility.constant import LABEL_TEST_VALUE
import utility.constant as constant
from utility.utility import logging
from utility.utility import list_namespaced_pod
from utility.utility import get_retry_count_and_interval

from datetime import datetime
from datetime import timezone


class recurringjob_keywords:

    def __init__(self):
        self.recurringjob = RecurringJob()

    def cleanup_recurringjobs(self):
        recurringjobs = self.recurringjob.list(
            label_selector=f"{LABEL_TEST}={LABEL_TEST_VALUE}"
        )

        logging(f'Cleaning up {len(recurringjobs)} recurringjobs')
        for recurringjob in recurringjobs:
            self.recurringjob.delete(recurringjob['metadata']['name'])

    def create_recurringjob(self, job_name, task, groups="[]", cron="*/2 * * * *", concurrency=1, labels="{}"):
        groups = ast.literal_eval(groups)
        labels = ast.literal_eval(labels)

        logging(f"Creating recurringjob {job_name}, task={task}, groups={groups}, cron={cron}, concurrency={concurrency}, labels={labels}")
        self.recurringjob.create(job_name, task=task, groups=groups, cron=cron, concurrency=concurrency, labels=labels)

    def create_recurringjob_for_volume(self, volume_name, task, cron="*/2 * * * *"):
        job_name = volume_name + '-' + task

        logging(f'Creating recurringjob {job_name} for volume {volume_name}')
        self.recurringjob.create(job_name, task=task, cron=cron)
        self.recurringjob.add_to_volume(job_name, volume_name)

    def check_recurringjobs_work(self, volume_name):
        logging(f'Checking recurringjobs work for volume {volume_name}')
        self.recurringjob.check_jobs_work(volume_name)

    def check_recurringjob_work_for_volume(self, job_name, job_task, volume_name):
        self.recurringjob.check_recurringjob_work_for_volume(job_name, job_task, volume_name)

    def create_system_backup_recurringjob(self, job_name, parameters={'volume-backup-policy': 'if-not-present'}):
        logging(f'Creating system-backup recurringjob {job_name} with parameters {parameters}')
        self.recurringjob.create(job_name, task="system-backup", parameters=parameters)

    def wait_for_recurringjob_created_systembackup_state(self, job_name, expected_state):
        logging(f'Waiting for recurringjob {job_name} created systembackup to reach state {expected_state}')
        self.recurringjob.wait_for_systembackup_state(job_name, expected_state)

    def assert_recurringjob_created_backup_for_volume(self, volume_name, job_name, retry_count=-1):
        logging(f'Checking recurringjob {job_name} created backup for volume {volume_name}')
        self.recurringjob.assert_recurringjob_created_backup_for_volume(volume_name, job_name, retry_count=retry_count)

    def wait_for_recurringjob_pod_completion_without_error(self, job_name):
        logging(f'Waiting for recurringjob {job_name} pod completion without error')
        self.recurringjob.wait_for_pod_completion_without_error(job_name)

    def wait_for_recurringjob_pod_completion(self, job_name):
        logging(f'Waiting for recurringjob {job_name} pod completion')
        self.recurringjob.wait_for_recurringjob_pod_completion(job_name)

    def check_recurringjob_concurrency(self, job_name, concurrency):
        self.recurringjob.check_recurringjob_concurrency(job_name, concurrency)

    def update_recurringjob(self, job_name, groups=None, cron=None, concurrency=None, labels=None, parameters=None):
        self.recurringjob.update_recurringjob(job_name, groups, cron, concurrency, labels, parameters)

    def wait_for_recurringjob_pod_create(self, job_name):
        logging(f'Waiting for recurringjob {job_name} pod start')
        start_time = datetime.now(timezone.utc)
        retry_count, retry_interval = get_retry_count_and_interval()

        for i in range(retry_count):
            pods = list_namespaced_pod(constant.LONGHORN_NAMESPACE, f"recurring-job.longhorn.io={job_name}")
            for pod in pods:
                if pod.metadata.creation_timestamp and pod.metadata.creation_timestamp > start_time:
                    logging(f"Pod {pod.metadata.name} created at {pod.metadata.creation_timestamp}")
                    return
            time.sleep(retry_interval)

        assert False, f"No new pod of {job_name} is created after {start_time}"
