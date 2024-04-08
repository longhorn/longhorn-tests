import time

from kubernetes import client

from recurringjob.base import Base
from recurringjob.constant import RETRY_COUNTS
from recurringjob.constant import RETRY_INTERVAL
from recurringjob.rest import Rest

from utility.constant import LABEL_TEST
from utility.constant import LABEL_TEST_VALUE
from utility.utility import logging


class CRD(Base):

    def __init__(self):
        self.rest = Rest()
        self.batch_v1_api = client.BatchV1Api()
        self.obj_api = client.CustomObjectsApi()

    def create(self, name, task, groups, cron, retain, concurrency, label):
        body = {
            "apiVersion": "longhorn.io/v1beta2",
            "kind": "RecurringJob",
            "metadata": {
                "name": name,
                "labels": {
                    LABEL_TEST: LABEL_TEST_VALUE
                }
            },
            "spec": {
                "name": name,
                "groups": groups,
                "task": task,
                "cron": cron,
                "retain": retain,
                "concurrency": concurrency,
                "labels": label
            }
        }
        self.obj_api.create_namespaced_custom_object(
            group="longhorn.io",
            version="v1beta2",
            namespace="longhorn-system",
            plural="recurringjobs",
            body=body
        )

        return self.wait_for_cron_job_create(name)

    def delete(self, recurringjob_name):
        try:
            self.obj_api.delete_namespaced_custom_object(
                group="longhorn.io",
                version="v1beta2",
                namespace="longhorn-system",
                plural="recurringjobs",
                name=recurringjob_name,
                body=client.V1DeleteOptions(),
            )
        except Exception as e:
            logging(f"Failed to delete recurringjob {recurringjob_name}: {e}")
            return False

    def get(self, name):
        return self.obj_api.get_namespaced_custom_object(
            group="longhorn.io",
            version="v1beta2",
            namespace="longhorn-system",
            plural="recurringjobs",
            name=name,
        )

    def list(self, label_selector=None):
        return self.obj_api.list_namespaced_custom_object(
            group="longhorn.io",
            version="v1beta2",
            namespace="longhorn-system",
            plural="recurringjobs",
            label_selector=label_selector
        )

    def add_to_volume(self, job_name, volume_name):
        logging("Delegating the add_to_volume call to API because there is no CRD implementation")
        return self.rest.add_to_volume(job_name, volume_name)

    def check_jobs_work(self, volume_name):
        logging("Delegating the check_jobs_work call to API because there is no CRD implementation")
        return self.rest.check_jobs_work(volume_name)

    def wait_for_cron_job_create(self, job_name):
        is_created = False
        for _ in range(RETRY_COUNTS):
            job = self.batch_v1_api.list_namespaced_cron_job(
                'longhorn-system',
                label_selector=f"recurring-job.longhorn.io={job_name}"
            )
            if len(job.items) != 0:
                is_created = True
                break
            time.sleep(RETRY_INTERVAL)
        assert is_created
