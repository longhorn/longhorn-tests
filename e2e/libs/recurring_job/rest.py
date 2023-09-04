import time
import logging
from kubernetes import client
from recurring_job.base import Base
from utility.utility import get_longhorn_client
from utility.utility import filter_cr
from datetime import datetime

RETRY_COUNTS = 180
RETRY_INTERVAL = 1

class Rest(Base):

    def __init__(self):
        self.client = get_longhorn_client()
        self.batch_v1_api = client.BatchV1Api()

    def create(self, name, task, groups, cron, retain, concurrency, labels):
        self.client.create_recurring_job(
            Name=name,
            Task=task,
            Groups=groups,
            Cron=cron,
            Retain=retain,
            Concurrency=concurrency,
            Labels=labels)
        self._wait_for_cron_job_create(name)

    def delete(self, job_name, volume_name):
        self.client.delete(self.get(job_name))
        self._wait_for_cron_job_delete(job_name)
        self._wait_for_volume_recurring_job_delete(job_name, volume_name)

    def get(self, name):
        return self.client.by_id_recurring_job(name)

    def add_to_volume(self, job_name, volume_name):
        volume = self.client.by_id_volume(volume_name)
        volume.recurringJobAdd(name=job_name, isGroup=False)
        self._wait_for_volume_recurring_job_update(job_name, volume_name)

    def _wait_for_volume_recurring_job_update(self, job_name, volume_name):
        updated = False
        for _ in range(RETRY_COUNTS):
            jobs, _ = self.get_volume_recurring_jobs_and_groups(volume_name)
            if job_name in jobs:
                updated = True
                break
            time.sleep(RETRY_INTERVAL)
        assert updated

    def _wait_for_volume_recurring_job_delete(self, job_name, volume_name):
        deleted = False
        for _ in range(RETRY_COUNTS):
            jobs, _ = self.get_volume_recurring_jobs_and_groups(volume_name)
            if job_name not in jobs:
                deleted = True
                break
            time.sleep(RETRY_INTERVAL)
        assert deleted

    def get_volume_recurring_jobs_and_groups(self, volume_name):
        volume = self.client.by_id_volume(volume_name)
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
        # recurring job following the cron schedule
        # currently only support checking normal snapshot/backup
        # every 1 min recurring job
        jobs, _ = self.get_volume_recurring_jobs_and_groups(volume_name)
        for job_name in jobs:
            job = self.get(job_name)
            logging.warn(f"get recurring job: {job}")
            if job['task'] == 'snapshot' and job['cron'] == '* * * * *':
                period_in_sec = 60
                self._check_snapshot_created_in_time(volume_name, job_name, period_in_sec)
            elif job['task'] == 'backup' and job['cron'] == '* * * * *':
                period_in_sec = 60
                self._check_backup_created_in_time(volume_name, period_in_sec)

    def _check_snapshot_created_in_time(self, volume_name, job_name, period_in_sec):
        # check snapshot can be created by the recurring job
        current_time = datetime.utcnow()
        logging.warn(f"current_time = {current_time}")
        current_timestamp = current_time.timestamp()
        logging.warn(f"current_timestamp = {current_timestamp}")
        label_selector=f"longhornvolume={volume_name}"
        snapshot_timestamp = 0
        for _ in range(period_in_sec * 2):
            snapshot_list = filter_cr("longhorn.io", "v1beta2", "longhorn-system", "snapshots", label_selector=label_selector)
            try:
                if len(snapshot_list['items']) > 0:
                    for item in snapshot_list['items']:
                        # this snapshot can be created by snapshot or backup recurring job
                        # but job_name is in spec.labels.RecurringJob
                        # and crd doesn't support field selector
                        # so need to filter by ourselves
                        if item['spec']['labels']['RecurringJob'] == job_name:
                            logging.warn(f"item = {item}")
                            snapshot_time = snapshot_list['items'][0]['metadata']['creationTimestamp']
                            logging.warn(f"snapshot_time = {snapshot_time}")
                            snapshot_time = datetime.strptime(snapshot_time, '%Y-%m-%dT%H:%M:%SZ')
                            logging.warn(f"snapshot_time = {snapshot_time}")
                            snapshot_timestamp = snapshot_time.timestamp()
                            logging.warn(f"snapshot_timestamp = {snapshot_timestamp}")
                            break
                    if snapshot_timestamp > current_timestamp:
                        return
            except Exception as e:
                logging.warn(f"iterate snapshot list error: {e}")
            time.sleep(1)
        assert False, f"since {current_time},\
                        there's no new snapshot created by recurring job \
                        {snapshot_list}"

    def _check_backup_created_in_time(self, volume_name, period_in_sec):
        # check backup can be created by the recurring job
        current_time = datetime.utcnow()
        logging.warn(f"current_time = {current_time}")
        current_timestamp = current_time.timestamp()
        logging.warn(f"current_timestamp = {current_timestamp}")
        label_selector=f"backup-volume={volume_name}"
        backup_timestamp = 0
        for _ in range(period_in_sec * 2):
            backup_list = filter_cr("longhorn.io", "v1beta2", "longhorn-system", "backups", label_selector=label_selector)
            try:
                if len(backup_list['items']) > 0:
                    backup_time = backup_list['items'][0]['metadata']['creationTimestamp']
                    logging.warn(f"backup_time = {backup_time}")
                    backup_time = datetime.strptime(backup_time, '%Y-%m-%dT%H:%M:%SZ')
                    logging.warn(f"backup_time = {backup_time}")
                    backup_timestamp = backup_time.timestamp()
                    logging.warn(f"backup_timestamp = {backup_timestamp}")
                if backup_timestamp > current_timestamp:
                    return
            except Exception as e:
                logging.warn(f"iterate backup list error: {e}")
            time.sleep(1)
        assert False, f"since {current_time},\
                        there's no new backup created by recurring job \
                        {backup_list}"

    def cleanup(self, volume_names):
        for volume_name in volume_names:
            jobs, _ = self.get_volume_recurring_jobs_and_groups(volume_name)
            for job in jobs:
                self.delete(job, volume_name)