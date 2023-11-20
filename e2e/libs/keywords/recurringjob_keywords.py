from recurringjob import RecurringJob

from utility.utility import logging


class recurringjob_keywords:

    def __init__(self):
        self.recurringjob = RecurringJob()

    def create_snapshot_recurringjob_for_volume(self, volume_name):
        job_name = volume_name + '-snap'
        self.recurringjob.create(job_name, task="snapshot")
        self.recurringjob.add_to_volume(job_name, volume_name)
        self.recurringjob.get(job_name)
        logging(f'Created recurringjob {job_name} for volume {volume_name}')

    def create_backup_recurringjob_for_volume(self, volume_name):
        job_name = volume_name + '-bak'
        self.recurringjob.create(job_name, task="backup")
        self.recurringjob.add_to_volume(job_name, volume_name)
        self.recurringjob.get(job_name)
        logging(f'Created recurringjob {job_name} for volume {volume_name}')

    def check_recurringjobs_work(self, volume_name):
        self.recurringjob.check_jobs_work(volume_name)

    def cleanup_recurringjobs(self, volume_names):
        self.recurringjob.cleanup(volume_names)
