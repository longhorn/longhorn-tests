import time
import json
from datetime import datetime
import re
from collections import Counter

from kubernetes import client
from kubernetes import watch

from recurringjob.base import Base
from recurringjob.constant import RETRY_COUNTS
from recurringjob.constant import RETRY_INTERVAL
from recurringjob.rest import Rest
from volume.crd import CRD as VolumeCRD

from utility.constant import LABEL_TEST
from utility.constant import LABEL_TEST_VALUE
import utility.constant as constant
from utility.utility import filter_cr
from utility.utility import get_retry_count_and_interval
from utility.utility import logging
from utility.utility import subprocess_exec_cmd
from utility.utility import get_cron_after


class CRD(Base):

    def __init__(self):
        self.rest = Rest()
        self.core_v1_api = client.CoreV1Api()
        self.batch_v1_api = client.BatchV1Api()
        self.obj_api = client.CustomObjectsApi()
        self.retry_count, self.retry_interval = get_retry_count_and_interval()

    def create(self, name, task, groups, cron, retain, concurrency, label, parameters):
        if "minutes from now" in cron:
            minutes = int(cron.split()[0])
            cron = get_cron_after(minutes)
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
                "labels": label,
                "parameters": parameters
            }
        }
        self.obj_api.create_namespaced_custom_object(
            group="longhorn.io",
            version="v1beta2",
            namespace=constant.LONGHORN_NAMESPACE,
            plural="recurringjobs",
            body=body
        )

        return self.wait_for_cron_job_create(name)

    def delete(self, recurringjob_name):
        try:
            self.obj_api.delete_namespaced_custom_object(
                group="longhorn.io",
                version="v1beta2",
                namespace=constant.LONGHORN_NAMESPACE,
                plural="recurringjobs",
                name=recurringjob_name,
                body=client.V1DeleteOptions(),
            )
        except Exception as e:
            logging(f"Failed to delete recurringjob {recurringjob_name}: {e}")
            return False

    def get(self, name):
        cmd = f"kubectl get recurringjobs -n {constant.LONGHORN_NAMESPACE} {name} -ojson"
        return json.loads(subprocess_exec_cmd(cmd))

    def list(self, label_selector=None):
        label_selector = f"-l {label_selector}" if label_selector else ""
        cmd = f"kubectl get recurringjobs -n {constant.LONGHORN_NAMESPACE} {label_selector} -ojson"
        return json.loads(subprocess_exec_cmd(cmd))["items"]

    def add_to_volume(self, job_name, volume_name):
        logging("Delegating the add_to_volume call to API because there is no CRD implementation")
        return self.rest.add_to_volume(job_name, volume_name)

    def get_volume_recurringjobs_and_groups(self, volume_name):
        for i in range(self.retry_count):
            try:
                jobs = VolumeCRD().get_volume_recurringjobs(volume_name)
                groups = VolumeCRD().get_volume_recurringjob_groups(volume_name)
                return jobs, groups
            except Exception as e:
                logging(f"Getting volume {volume_name} recurring jobs and groups error: {e}")
            time.sleep(self.retry_interval)
        assert False, f"Failed to get volume {volume_name} recurring jobs and groups"

    def check_jobs_work(self, volume_name):
        jobs, groups = self.get_volume_recurringjobs_and_groups(volume_name)
        # handle jobs
        for job_name in jobs:
            job = self.get(job_name)
            logging(f"Checking recurring job {job}")
            if job['spec']['task'] == 'snapshot':
                self.check_volume_snapshot_created_by_recurringjob(volume_name, job_name)
            elif job['spec']['task'] == 'backup':
                self.check_volume_backup_created_by_recurringjob(volume_name, job_name)
            else:
                assert False, f"Unhandled recurring job {job}"
        # handle groups
        all_jobs = self.list()
        group_jobs = []
        for job in all_jobs:
            if any(g in job['spec']['groups'] for g in groups):
                group_jobs.append(job['spec']['name'])
        for job_name in group_jobs:
            job = self.get(job_name)
            logging(f"Checking recurring job {job}")
            if job['spec']['task'] == 'snapshot':
                self.check_volume_snapshot_created_by_recurringjob(volume_name, job_name)
            elif job['spec']['task'] == 'backup':
                self.check_volume_backup_created_by_recurringjob(volume_name, job_name)
            else:
                assert False, f"Unhandled recurring job {job}"

    def check_recurringjob_work_for_volume(self, job_name, job_task, volume_name):
        logging(f"Checking {job_task} is created for volume {volume_name} by recurring job {job_name}")
        if job_task == 'snapshot':
            self.check_volume_snapshot_created_by_recurringjob(volume_name, job_name)
        elif job_task == 'backup':
            self.check_volume_backup_created_by_recurringjob(volume_name, job_name)
        else:
            assert False, f"Unhandled recurring job task {job_task}"

    def check_volume_snapshot_created_by_recurringjob(self, volume_name, job_name):
        # check snapshot can be created by the recurringjob
        current_time = datetime.utcnow()
        current_timestamp = current_time.timestamp()
        label_selector=f"longhornvolume={volume_name}"
        snapshot_timestamp = 0
        for i in range(self.retry_count):
            self.delete_expired_pending_recurringjob_pod(job_name)

            logging(f"Waiting for {volume_name} new snapshot created ({i}) ...")
            snapshot_list = filter_cr("longhorn.io", "v1beta2", constant.LONGHORN_NAMESPACE, "snapshots", label_selector=label_selector)
            try:
                if len(snapshot_list['items']) > 0:
                    for item in snapshot_list['items']:
                        # this snapshot can be created by snapshot or backup recurringjob
                        # but job_name is in spec.labels.RecurringJob
                        # and crd doesn't support field selector
                        # so need to filter by ourselves
                        if item['spec']['labels'] and 'RecurringJob' in item['spec']['labels'] and \
                            item['spec']['labels']['RecurringJob'] == job_name and \
                            item['status']['readyToUse'] == True:
                            snapshot_time = item['metadata']['creationTimestamp']
                            snapshot_time = datetime.strptime(snapshot_time, '%Y-%m-%dT%H:%M:%SZ')
                            snapshot_timestamp = snapshot_time.timestamp()
                        if snapshot_timestamp > current_timestamp:
                            logging(f"Got snapshot {item}, create time = {snapshot_time}, timestamp = {snapshot_timestamp}")
                            return
            except Exception as e:
                logging(f"Iterating snapshot list error: {e}")
            time.sleep(self.retry_interval)
        assert False, f"since {current_time},\
                        there's no new snapshot created by recurringjob \
                        {snapshot_list}"

    def check_volume_backup_created_by_recurringjob(self, volume_name, job_name, retry_count=-1):
        if retry_count == -1:
            retry_count = self.retry_count

        # check backup can be created by the recurringjob
        current_time = datetime.utcnow()
        current_timestamp = current_time.timestamp()
        label_selector=f"backup-volume={volume_name}"
        backup_timestamp = 0
        for i in range(retry_count):
            self.delete_expired_pending_recurringjob_pod(job_name)

            logging(f"Waiting for {volume_name} new backup created ({i}) ...")
            backup_list = filter_cr("longhorn.io", "v1beta2", constant.LONGHORN_NAMESPACE, "backups", label_selector=label_selector)
            try:
                if len(backup_list['items']) > 0:
                    for item in backup_list['items']:
                        state = item['status']['state']
                        if state != "Completed":
                            continue
                        backup_time = item['metadata']['creationTimestamp']
                        backup_time = datetime.strptime(backup_time, '%Y-%m-%dT%H:%M:%SZ')
                        backup_timestamp = backup_time.timestamp()
                        if backup_timestamp > current_timestamp:
                            logging(f"Got backup {item}, create time = {backup_time}, timestamp = {backup_timestamp}")
                            return
            except Exception as e:
                logging(f"Iterating backup list error: {e}")
            time.sleep(self.retry_interval)
        assert False, f"since {current_time},\
                        there's no new backup created by recurringjob \
                        {backup_list}"

    def delete_expired_pending_recurringjob_pod(self, job_name, namespace=constant.LONGHORN_NAMESPACE, expiration_seconds=5 * 60):
        """
        Deletes expired pending recurring job pods in the specified namespace.

        This method lists all pods in the given namespace with the label
        `recurring-job.longhorn.io={job_name}` and status `Pending`.
        It calculates the age of each pod and deletes those that have been
        pending for longer than the specified expiration time.

        This is a workaround for an upstream issue where CronJob pods may remain
        stuck in the `Pending` state indefinitely after a node reboot.
        Issue: https://github.com/longhorn/longhorn/issues/7956
        """
        try:
            pod_list = self.core_v1_api.list_namespaced_pod(
                namespace=namespace,
                label_selector=f"recurring-job.longhorn.io={job_name}"
            )
            for pod in pod_list.items:
                if pod.status.phase != "Pending":
                    continue

                pod_age = time.time() - pod.metadata.creation_timestamp.timestamp()
                if pod_age > expiration_seconds:
                    logging(f"Deleting expired pending recurringjob pod {pod.metadata.name}")
                    self.core_v1_api.delete_namespaced_pod(
                        name=pod.metadata.name,
                        namespace=namespace,
                        grace_period_seconds=0
                    )
                    logging(f"Deleted pod {pod.metadata.name}")
                else:
                    logging(f"Recurringjob pod {pod.metadata.name} in Pending state,\
                        age {pod_age:.2f} < expiration {expiration_seconds}s")
        except Exception as e:
            logging(f"Failed to delete expired pending recurringjob pods: {e}")

    def wait_for_cron_job_create(self, job_name):
        is_created = False
        for _ in range(RETRY_COUNTS):
            job = self.batch_v1_api.list_namespaced_cron_job(
                constant.LONGHORN_NAMESPACE,
                label_selector=f"recurring-job.longhorn.io={job_name}"
            )
            if len(job.items) != 0:
                is_created = True
                break
            time.sleep(RETRY_INTERVAL)
        assert is_created

    def wait_for_systembackup_state(self, job_name, expected_state):
        for i in range(self.retry_count):

            time.sleep(self.retry_interval)

            system_backup_list = filter_cr("longhorn.io", "v1beta2", constant.LONGHORN_NAMESPACE, "systembackups",
                                           label_selector=f"recurring-job.longhorn.io/system-backup={job_name}")
            try:
                if len(system_backup_list['items']) == 0:
                    logging(f"Waiting for systembackup to be created by job {job_name} ... ({i})")
                    continue

                for item in system_backup_list['items']:
                    state = item['status']['state']
                    logging(f"Waiting for systembackup created by job {job_name} in state '{state}' to reach state '{expected_state}' ... ({i})")
                    if state == expected_state:
                        return

            except Exception as e:
                logging(f"Waiting for systembackup created by job {job_name} to reach state {expected_state} failed: {e}")

        assert False, f"Waiting for systembackup created by job {job_name} to reach state {expected_state} failed"

    def assert_volume_backup_created(self, volume_name, job_name, retry_count=-1):
        self.check_volume_backup_created_by_recurringjob(volume_name, job_name, retry_count=retry_count)

    def wait_for_pod_completion_without_error(self, job_name, namespace=constant.LONGHORN_NAMESPACE):
        """
        Waits for the completion of a pod associated with a recurring job and ensures it completes without errors.

        This method watches runtime pod status updates and checks for error conditions:
          - Waiting states such as CrashLoopBackOff or Error,
          - Current container terminations with non-zero exit codes,
          - Previous container terminations from restarts (via lastState),
          - Unexpected container restarts (restart_count > 0), even if the pod eventually succeeds.

        If any of these conditions are encountered, the method raises an exception immediately,
        indicating the pod may have failed or been unstable.
        """
        timeout_seconds = 30 * 60   # 30 minutes timeout

        w = watch.Watch()
        for event in w.stream(
            self.core_v1_api.list_namespaced_pod,
            namespace=namespace,
            label_selector=f"recurring-job.longhorn.io={job_name}",
            timeout_seconds=timeout_seconds
        ):
            pod = event['object']
            pod_name = pod.metadata.name
            status = pod.status.phase
            logging(f"Pod {pod_name} status: {status}")

            if pod.status.container_statuses:
                for container_status in pod.status.container_statuses:
                    name = container_status.name
                    state = container_status.state
                    last_state = container_status.last_state

                    # Check for waiting states like CrashLoopBackOff
                    if state.waiting:
                        reason = state.waiting.reason
                        logging(f"Container {name} is waiting: {reason}")
                        if reason in ["CrashLoopBackOff", "Error"]:
                            w.stop()
                            raise Exception(
                                f"Pod {pod_name} container {name} is in {reason} state. "
                                "Recurring job may have failed."
                            )

                    # Check for current terminated state with non-zero exit code
                    if state.terminated:
                        exit_code = state.terminated.exit_code
                        logging(f"Container {name} is terminated with exit code {exit_code}")
                        if exit_code != 0:
                            w.stop()
                            raise Exception(
                                f"Pod {pod_name} container {name} terminated with exit code {exit_code}. "
                                "Recurring job may have failed."
                            )

                    # Check previous termination via lastState for recent crashes
                    if last_state and last_state.terminated and last_state.terminated.exit_code != 0:
                        reason = last_state.terminated.reason or "Unknown"
                        exit_code = last_state.terminated.exit_code
                        logging(f"Container {name} previously terminated with exit code {exit_code} (reason: {reason})")
                        w.stop()
                        raise Exception(
                            f"Container '{name}' in pod '{pod_name}' previously terminated with exit code {exit_code} "
                            f"(reason: {reason}). Recurring job may have crashed and restarted."
                        )

                    # If the container has restarted, we consider it unstable
                    # even if it eventually succeeded.
                    if container_status.restart_count > 0:
                        logging(f"Container {name} has restarted {container_status.restart_count} times")
                        w.stop()
                        raise Exception(
                            f"Pod {pod_name} container {name} restarted {container_status.restart_count} times. "
                            "Recurring job may have been unstable even if it eventually succeeded."
                        )

            if status == "Succeeded":
                logging(f"Pod {pod_name} for recurring job {job_name} completed successfully.")
                w.stop()
                return
            elif status == "Failed":
                logging(f"Pod {pod_name} for recurring job {job_name} failed.")
                w.stop()
                raise Exception(f"Recurring job {job_name} pod failed.")

        w.stop()
        raise Exception(f"Recurring job {job_name} did not complete successfully within the timeout ({timeout_seconds} seconds).")

    def wait_for_recurringjob_pod_completion(self, job_name, namespace=constant.LONGHORN_NAMESPACE):
        timeout_seconds = 30 * 60   # 30 minutes timeout

        w = watch.Watch()
        for event in w.stream(
            self.core_v1_api.list_namespaced_pod,
            namespace=namespace,
            label_selector=f"recurring-job.longhorn.io={job_name}",
            timeout_seconds=timeout_seconds
        ):
            pod = event['object']
            pod_name = pod.metadata.name
            status = pod.status.phase
            logging(f"Pod {pod_name} status: {status}")

            if status == "Succeeded":
                logging(f"Pod {pod_name} for recurring job {job_name} completed successfully (Succeeded).")
                w.stop()
                return

        w.stop()
        raise Exception(f"Recurring job {job_name} did not succeed within the timeout ({timeout_seconds} seconds).")

    def check_recurringjob_concurrency(self, job_name, concurrency):
        # monitor the recurring job for 5 minutes to confirm the concurrency
        # the log looks like:
        # time="2025-10-08T03:58:00.800807962Z" level=info msg="Creating volume job"
        pattern = re.compile(r'time="[^T]+T(\d{2}:\d{2}:\d{2})\.\d+Z".*Creating volume job')
        cmd = f"kubectl logs -l recurring-job.longhorn.io={job_name} -n {constant.LONGHORN_NAMESPACE}"
        checked = False
        timestamps = None
        for i in range(60):
            try:
                logs = subprocess_exec_cmd(cmd)
            except Exception as e:
                logging(f"Failed to get {job_name} logs: {e}")
            timestamps = pattern.findall(logs)
            if not timestamps:
                logging(f"No job created for {job_name}")
            else:
                counts = Counter(timestamps)
                for timestamp, count in sorted(counts.items()):
                    logging(f"{count} jobs created at {timestamp} for {job_name}")
                    if count == int(concurrency):
                        checked = True
                    elif count > int(concurrency):
                        logging(f"Recurring job {job_name} concurrency is {concurrency}, but there are {count} jobs created concurrently")
                        time.sleep(self.retry_count)
                        assert False, f"Recurring job {job_name} concurrency is {concurrency}, but there are {count} jobs created concurrently"
            time.sleep(5)
        assert checked, f"Recurring job {job_name} concurrency is {concurrency}, but can't find {concurrency} jobs created concurrently"

    def update_recurringjob(self, job_name, groups, cron, concurrency, labels, parameters):
        patch_data = {"spec": {}}
        if groups is not None:
            patch_data["spec"]["groups"] = groups
        if cron is not None:
            patch_data["spec"]["cron"] = cron
        if concurrency is not None:
            patch_data["spec"]["concurrency"] = int(concurrency)
        if labels is not None:
            patch_data["spec"]["labels"] = labels
        if parameters is not None:
            patch_data["spec"]["parameters"] = parameters
        patch_json = json.dumps(patch_data)
        cmd = f"kubectl -n {constant.LONGHORN_NAMESPACE} patch recurringjob {job_name} --type merge -p '{patch_json}'"
        subprocess_exec_cmd(cmd)
