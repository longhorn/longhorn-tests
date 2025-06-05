import time

from kubernetes import client
from kubernetes import watch

from recurringjob.base import Base
from recurringjob.constant import RETRY_COUNTS
from recurringjob.constant import RETRY_INTERVAL
from recurringjob.rest import Rest

from utility.constant import LABEL_TEST
from utility.constant import LABEL_TEST_VALUE
from utility.constant import LONGHORN_NAMESPACE
from utility.utility import filter_cr
from utility.utility import get_retry_count_and_interval
from utility.utility import logging


class CRD(Base):

    def __init__(self):
        self.rest = Rest()
        self.core_v1_api = client.CoreV1Api()
        self.batch_v1_api = client.BatchV1Api()
        self.obj_api = client.CustomObjectsApi()
        self.retry_count, self.retry_interval = get_retry_count_and_interval()

    def create(self, name, task, groups, cron, retain, concurrency, label, parameters):
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

    def wait_for_systembackup_state(self, job_name, expected_state):
        for i in range(self.retry_count):
            system_backup_list = filter_cr("longhorn.io", "v1beta2", "longhorn-system", "systembackups",
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

            time.sleep(self.retry_interval)
        assert False, f"Waiting for systembackup created by job {job_name} to reach state {expected_state} failed"

    def assert_volume_backup_created(self, volume_name, job_name, retry_count=-1):
        logging("Delegating the assert_volume_backup_created call to API because there is no CRD implementation")
        return self.rest.assert_volume_backup_created(volume_name, job_name, retry_count=retry_count)

    def wait_for_pod_completion_without_error(self, job_name, namespace=LONGHORN_NAMESPACE):
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
