import time

from kubernetes import client

from recurringjob.base import Base

import utility.constant as constant
from utility.utility import filter_cr
from utility.utility import get_longhorn_client
from utility.utility import logging
from utility.utility import get_retry_count_and_interval


class Rest(Base):

    def __init__(self):
        self.batch_v1_api = client.BatchV1Api()
        self.core_v1_api = client.CoreV1Api()
        self.retry_count, self.retry_interval = get_retry_count_and_interval()

    def create(self, name, task, groups, cron, retain, concurrency, labels, parameters):
        get_longhorn_client().create_recurring_job(
            Name=name,
            Task=task,
            Groups=groups,
            Cron=cron,
            Retain=retain,
            Concurrency=concurrency,
            Labels=labels,
            Parameters=parameters)
        self._wait_for_cron_job_create(name)

    def delete(self, job_name, volume_name):
        get_longhorn_client().delete(self.get(job_name))
        self._wait_for_cron_job_delete(job_name)
        self._wait_for_volume_recurringjob_delete(job_name, volume_name)

    def get(self, name):
        return get_longhorn_client().by_id_recurring_job(name)

    def add_to_volume(self, job_name, volume_name):
        volume = get_longhorn_client().by_id_volume(volume_name)
        volume.recurringJobAdd(name=job_name, isGroup=False)
        self._wait_for_volume_recurringjob_update(job_name, volume_name)

    def _wait_for_volume_recurringjob_update(self, job_name, volume_name):
        updated = False
        for _ in range(self.retry_count):
            jobs, _ = self.get_volume_recurringjobs_and_groups(volume_name)
            if job_name in jobs:
                updated = True
                break
            time.sleep(self.retry_interval)
        assert updated

    def _wait_for_volume_recurringjob_delete(self, job_name, volume_name):
        deleted = False
        for _ in range(self.retry_count):
            jobs, _ = self.get_volume_recurringjobs_and_groups(volume_name)
            if job_name not in jobs:
                deleted = True
                break
            time.sleep(self.retry_interval)
        assert deleted

    def get_volume_recurringjobs_and_groups(self, volume_name):
        for _ in range(self.retry_count):
            volume = None
            try:
                volume = get_longhorn_client().by_id_volume(volume_name)
                list = volume.recurringJobList()
                jobs = []
                groups = []
                for item in list:
                    if item['isGroup']:
                        groups.append(item['name'])
                    else:
                        jobs.append(item['name'])
                return jobs, groups
            except Exception as e:
                logging(f"Getting volume {volume} recurringjob list error: {e}")
                time.sleep(self.retry_interval)

    def _wait_for_cron_job_create(self, job_name):
        created = False
        for _ in range(self.retry_count):
            job = self.batch_v1_api.list_namespaced_cron_job(
                constant.LONGHORN_NAMESPACE,
                label_selector=f"recurring-job.longhorn.io={job_name}")
            if len(job.items) != 0:
                created = True
                break
            time.sleep(self.retry_interval)
        assert created

    def _wait_for_cron_job_delete(self, job_name):
        deleted = False
        for _ in range(self.retry_count):
            job = self.batch_v1_api.list_namespaced_cron_job(
                constant.LONGHORN_NAMESPACE,
                label_selector=f"recurring-job.longhorn.io={job_name}")
            if len(job.items) == 0:
                deleted = True
                break
            time.sleep(self.retry_interval)
        assert deleted

    def cleanup(self, volume_names):
        for volume_name in volume_names:
            logging(f"Cleaning up recurringjobs for volume {volume_name}")
            jobs, _ = self.get_volume_recurringjobs_and_groups(volume_name)
            for job in jobs:
                logging(f"Deleting recurringjob {job}")
                self.delete(job, volume_name)

    def wait_for_systembackup_state(self, job_name, expected_state):
        return NotImplemented

    def wait_for_pod_completion_without_error(self, job_name, namespace=constant.LONGHORN_NAMESPACE):
        return NotImplemented

    def wait_for_recurringjob_pod_completion(self, job_name, namespace=constant.LONGHORN_NAMESPACE):
        return NotImplemented
