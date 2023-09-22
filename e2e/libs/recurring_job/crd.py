from utility.utility import logging
from recurring_job.base import Base
from recurring_job.rest import Rest
from kubernetes import client

class CRD(Base):

    def __init__(self):
        self.rest = Rest()

    def create(self, name, task, groups, cron, retain, concurrency, label):
        logging("Delegating the create call to API because there is no CRD implementation")
        return self.rest.create(name, task, groups, cron, retain, concurrency, label)

    def delete(self, job_name, volume_name):
        logging("Delegating the delete call to API because there is no CRD implementation")
        return self.rest.delete(job_name, volume_name)

    def get(self, name):
        return self.rest.get(name)

    def add_to_volume(self, job_name, volume_name):
        logging("Delegating the add_to_volume call to API because there is no CRD implementation")
        return self.rest.add_to_volume(job_name, volume_name)

    def check_jobs_work(self, volume_name):
        logging("Delegating the check_jobs_work call to API because there is no CRD implementation")
        return self.rest.check_jobs_work(volume_name)

    def cleanup(self, volume_names):
        logging("Delegating the cleanup call to API because there is no CRD implementation")
        return self.rest.cleanup(volume_names)