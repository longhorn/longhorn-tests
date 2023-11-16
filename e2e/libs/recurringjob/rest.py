import time

from datetime import datetime

from kubernetes import client

from recurringjob.base import Base
from recurringjob.constant import RETRY_COUNTS
from recurringjob.constant import RETRY_INTERVAL

from utility.utility import filter_cr
from utility.utility import get_longhorn_client
from utility.utility import logging


class Rest(Base):

    def __init__(self):
        self.longhorn_client = get_longhorn_client()
        self.batch_v1_api = client.BatchV1Api()

    def create(self, name, task, groups, cron, retain, concurrency, labels):
        self.longhorn_client.create_recurring_job(
            Name=name,
            Task=task,
            Groups=groups,
            Cron=cron,
            Retain=retain,
            Concurrency=concurrency,
            Labels=labels)
        self._wait_for_cron_job_create(name)

    def delete(self, job_name, volume_name):
        self.longhorn_client.delete(self.get(job_name))
        self._wait_for_cron_job_delete(job_name)
        self._wait_for_volume_recurringjob_delete(job_name, volume_name)

    def get(self, name):
        return self.longhorn_client.by_id_recurring_job(name)

    def add_to_volume(self, job_name, volume_name):
        volume = self.longhorn_client.by_id_volume(volume_name)
        volume.recurringJobAdd(name=job_name, isGroup=False)
        self._wait_for_volume_recurringjob_update(job_name, volume_name)

    def _wait_for_volume_recurringjob_update(self, job_name, volume_name):
        updated = False
        for _ in range(RETRY_COUNTS):
            jobs, _ = self.get_volume_recurringjobs_and_groups(volume_name)
            if job_name in jobs:
                updated = True
                break
            time.sleep(RETRY_INTERVAL)
        assert updated

    def _wait_for_volume_recurringjob_delete(self, job_name, volume_name):
        deleted = False
        for _ in range(RETRY_COUNTS):
            jobs, _ = self.get_volume_recurringjobs_and_groups(volume_name)
            if job_name not in jobs:
                deleted = True
                break
            time.sleep(RETRY_INTERVAL)
        assert deleted

    def get_volume_recurringjobs_and_groups(self, volume_name):
        volume = self.longhorn_client.by_id_volume(volume_name)
        list = volume.recurringJobList()
        jobs = []
        groups = []
        for item in list:
            if item['isGroup']:
                groups.append(item['name'])
            else:
                jobs.append(item['name'])
        return jobs, groups

    def _wait_for_cron_job_create(self, job_name):
        created = False
        for _ in range(RETRY_COUNTS):
            job = self.batch_v1_api.list_namespaced_cron_job(
                'longhorn-system',
                label_selector=f"recurring-job.longhorn.io={job_name}")
            if len(job.items) != 0:
                created = True
                break
            time.sleep(RETRY_INTERVAL)
        assert created

    def _wait_for_cron_job_delete(self, job_name):
        deleted = False
        for _ in range(RETRY_COUNTS):
            job = self.batch_v1_api.list_namespaced_cron_job(
                'longhorn-system',
                label_selector=f"recurring-job.longhorn.io={job_name}")
            if len(job.items) == 0:
                deleted = True
                break
            time.sleep(RETRY_INTERVAL)
        assert deleted

    def check_jobs_work(self, volume_name):
        # check if snapshot/backup is really created by the
        # recurringjob following the cron schedule
        # currently only support checking normal snapshot/backup
        # every 1 min recurringjob
        jobs, _ = self.get_volume_recurringjobs_and_groups(volume_name)
        for job_name in jobs:
            job = self.get(job_name)
            logging(f"Checking recurringjob {job}")
            if job['task'] == 'snapshot' and job['cron'] == '* * * * *':
                period_in_sec = 60
                self._check_snapshot_created_in_time(volume_name, job_name, period_in_sec)
            elif job['task'] == 'backup' and job['cron'] == '* * * * *':
                period_in_sec = 60
                self._check_backup_created_in_time(volume_name, period_in_sec)

    def _check_snapshot_created_in_time(self, volume_name, job_name, period_in_sec):
        # check snapshot can be created by the recurringjob
        current_time = datetime.utcnow()
        current_timestamp = current_time.timestamp()

        label_selector=f"longhornvolume={volume_name}"

        max_iterations = period_in_sec * 10
        for _ in range(max_iterations):
            time.sleep(1)

            snapshot_list = filter_cr("longhorn.io", "v1beta2", "longhorn-system", "snapshots", label_selector=label_selector)

            if snapshot_list['items'] is None:
                continue

            for item in snapshot_list['items']:
                # this snapshot can be created by snapshot or backup recurringjob
                # but job_name is in spec.labels.RecurringJob
                # and crd doesn't support field selector
                # so need to filter by ourselves
                if item['spec']['labels'] is None:
                    continue

                try:
                    assert item['spec']['labels']['RecurringJob'] == job_name
                except AssertionError:
                    continue

                snapshot_timestamp = datetime.strptime(snapshot_list['items'][0]['metadata']['creationTimestamp'], '%Y-%m-%dT%H:%M:%SZ').timestamp()

                if snapshot_timestamp > current_timestamp:
                    return

                logging(f"Snapshot {item['metadata']['name']} timestamp = {snapshot_timestamp} is not greater than {current_timestamp}")

        assert False, f"No new snapshot created by recurringjob {job_name} for {volume_name} since {current_time}"

    def _check_backup_created_in_time(self, volume_name, period_in_sec):
        # check backup can be created by the recurringjob
        current_time = datetime.utcnow()
        current_timestamp = current_time.timestamp()

        label_selector=f"backup-volume={volume_name}"

        max_iterations = period_in_sec * 10
        for _ in range(max_iterations):
            time.sleep(1)

            backup_list = filter_cr("longhorn.io", "v1beta2", "longhorn-system", "backups", label_selector=label_selector)

            if backup_list['items'] is None:
                continue

            for item in backup_list['items']:
                backup_timestamp = datetime.strptime(item['metadata']['creationTimestamp'], '%Y-%m-%dT%H:%M:%SZ').timestamp()

                if backup_timestamp > current_timestamp:
                    return

                logging(f"Backup {item['metadata']['name']} timestamp = {backup_timestamp} is not greater than {current_timestamp}")

        assert False, f"No new backup created by recurringjob for {volume_name} since {current_time}"

    def cleanup(self, volume_names):
        for volume_name in volume_names:
            logging(f"Cleaning up recurringjobs for volume {volume_name}")
            jobs, _ = self.get_volume_recurringjobs_and_groups(volume_name)
            for job in jobs:
                logging(f"Deleting recurringjob {job}")
                self.delete(job, volume_name)
