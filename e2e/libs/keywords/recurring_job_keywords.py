from utility.utility import get_test_case_namespace, generate_volume_name
from utility.utility import get_node, list_nodes
from utility.utility import get_test_pod_running_node, get_test_pod_not_running_node
from robot.libraries.BuiltIn import BuiltIn
from recurring_job import RecurringJob
import logging

class recurring_job_keywords:

    def __init__(self):
        logging.warn("initialize recurring_job_keywords class")
        self.recurring_job = RecurringJob()


    def create_snapshot_recurring_job_for_volume(self, volume_name):
        job_name = volume_name + '-snap'
        self.recurring_job.create(job_name, task="snapshot")
        self.recurring_job.add_to_volume(job_name, volume_name)
        self.recurring_job.get(job_name)
        logging.warn(f'==> create recurring job {job_name} for volume {volume_name}')


    def create_backup_recurring_job_for_volume(self, volume_name):
        job_name = volume_name + '-bak'
        self.recurring_job.create(job_name, task="backup")
        self.recurring_job.add_to_volume(job_name, volume_name)
        self.recurring_job.get(job_name)
        logging.warn(f'==> create recurring job {job_name} for volume {volume_name}')


    def check_recurring_jobs_work(self, volume_name):
        self.recurring_job.check_jobs_work(volume_name)


    def cleanup_recurring_jobs(self, volume_names):
        self.recurring_job.cleanup(volume_names)
