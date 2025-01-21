from recurringjob import RecurringJob

from utility.constant import LABEL_TEST
from utility.constant import LABEL_TEST_VALUE
from utility.utility import logging


class recurringjob_keywords:

    def __init__(self):
        self.recurringjob = RecurringJob()

    def cleanup_recurringjobs(self):
        recurringjobs = self.recurringjob.list(
            label_selector=f"{LABEL_TEST}={LABEL_TEST_VALUE}"
        )

        logging(f'Cleaning up {len(recurringjobs["items"])} recurringjobs')
        for recurringjob in recurringjobs['items']:
            self.recurringjob.delete(recurringjob['metadata']['name'])

    def create_snapshot_recurringjob_for_volume(self, volume_name):
        job_name = volume_name + '-snap'

        logging(f'Creating snapshot recurringjob {job_name} for volume {volume_name}')
        self.recurringjob.create(job_name, task="snapshot")
        self.recurringjob.add_to_volume(job_name, volume_name)

    def create_backup_recurringjob_for_volume(self, volume_name):
        job_name = volume_name + '-bak'

        logging(f'Creating backup recurringjob {job_name} for volume {volume_name}')
        self.recurringjob.create(job_name, task="backup")
        self.recurringjob.add_to_volume(job_name, volume_name)

    def check_recurringjobs_work(self, volume_name):
        logging(f'Checking recurringjobs work for volume {volume_name}')
        self.recurringjob.check_jobs_work(volume_name)

    def create_system_backup_recurringjob(self, job_name, parameters={'volume-backup-policy': 'if-not-present'}):
        logging(f'Creating system-backup recurringjob {job_name} with parameters {parameters}')
        self.recurringjob.create(job_name, task="system-backup", parameters=parameters)

    def wait_for_recurringjob_created_systembackup_state(self, job_name, expected_state):
        logging(f'Waiting for recurringjob {job_name} created systembackup to reach state {expected_state}')
        self.recurringjob.wait_for_systembackup_state(job_name, expected_state)

    def assert_recurringjob_created_backup_for_volume(self, volume_name, retry_count=-1):
        logging(f'Checking recurringjob created backup for volume {volume_name}')
        self.recurringjob.assert_recurringjob_created_backup_for_volume(volume_name, retry_count=retry_count)
