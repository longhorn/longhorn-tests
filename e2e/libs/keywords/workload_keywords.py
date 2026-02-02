import multiprocessing
import asyncio

from node import Node

from persistentvolumeclaim import PersistentVolumeClaim

from workload.pod import get_volume_name_by_pod
from workload.pod import new_busybox_manifest
from workload.pod import create_pod
from workload.pod import delete_pod
from workload.pod import list_pods
from workload.pod import cleanup_pods
from workload.pod import check_pod_did_not_restart
from workload.workload import get_workload_pod_data_checksum
from workload.workload import check_workload_pod_data_checksum
from workload.workload import check_workload_pod_data_exists
from workload.workload import get_workload_pods
from workload.workload import get_workload_pod_names
from workload.workload import get_workload_persistent_volume_claim_name
from workload.workload import get_workload_volume_name
from workload.workload import is_workload_pods_has_annotations
from workload.workload import is_workload_pods_has_cni_interface
from workload.workload import keep_writing_pod_data
from workload.workload import make_block_device_filesystem_in_workload_pod
from workload.workload import mount_block_device_in_workload_pod
from workload.workload import write_pod_random_data
from workload.workload import write_pod_large_data
from workload.workload import wait_for_workload_pods_container_creating
from workload.workload import wait_for_workload_pods_running
from workload.workload import wait_for_workload_pods_stable
from workload.workload import wait_for_workload_pod_kept_in_state
from workload.workload import get_pod_node
from workload.workload import run_commands_in_pod

from utility.constant import ANNOT_CHECKSUM
from utility.constant import ANNOT_EXPANDED_SIZE
from utility.constant import LABEL_LONGHORN_COMPONENT
import utility.constant as constant
from utility.utility import convert_size_to_bytes
from utility.utility import logging
from utility.utility import list_namespaced_pod

from volume import Volume
from datetime import datetime, timezone


class workload_keywords:

    def __init__(self):
        self.node = Node()
        self.persistentvolumeclaim = PersistentVolumeClaim()
        self.volume = Volume()

    def create_pod(self, pod_name, claim_name):
        logging(f'Creating pod {pod_name} using pvc {claim_name}')
        create_pod(new_busybox_manifest(pod_name, claim_name))

    def delete_pod(self, pod_name, namespace='default', wait=True):
        logging(f'Deleting pod {pod_name} in namespace {namespace}')
        delete_pod(pod_name, namespace, wait)

    def list_pods(self, namespace, label_selector):
        logging(f'Listing pods with label {label_selector} in namespace {namespace}')
        pods = list_pods(namespace, label_selector)
        return [pod.metadata.name for pod in pods]

    def cleanup_pods(self):
        cleanup_pods()

    def get_workload_pod_data_checksum(self, workload_name, file_name):
        logging(f'Getting checksum for file {file_name} in workload {workload_name}')
        return get_workload_pod_data_checksum(workload_name, file_name)

    def check_workload_pod_data_exists(self, workload_name, file_name):
        return check_workload_pod_data_exists(workload_name, file_name)

    def delete_workload_pod_on_node(self, workload_name, node_name, namespace="default", label_selector="", wait=True):
        pods = get_workload_pods(workload_name, namespace=namespace, label_selector=label_selector)
        for pod in pods:
            if pod.spec.node_name == node_name:
                logging(f'Deleting pod {pod.metadata.name} on node {node_name}')
                delete_pod(pod.metadata.name, namespace=namespace, wait=wait)

    def get_workload_pod_name(self, workload_name, namespace="default"):
        return get_workload_pod_names(workload_name, namespace)[0]

    def get_workload_persistent_volume_claim_name(self, workload_name):
        return get_workload_persistent_volume_claim_name(workload_name)

    def get_workload_volume_name(self, workload_name):
        return get_workload_volume_name(workload_name)

    def make_block_device_filesystem_in_workload_pod(self, workload_name):
        pod_name = get_workload_pod_names(workload_name)[0]

        logging(f'Making file system on block device in pod {pod_name}')
        make_block_device_filesystem_in_workload_pod(pod_name)

    def mount_block_device_in_workload_pod(self, workload_name, mount_point):
        pod_name = get_workload_pod_names(workload_name)[0]

        logging(f'Mounting block device on {mount_point} in pod {pod_name}')
        mount_block_device_in_workload_pod(pod_name, mount_point)

    def write_workload_pod_random_data(self, workload_name, size_in_mb, file_name):
        pod_name = get_workload_pod_names(workload_name)[0]

        logging(f'Writing {size_in_mb} MB random data to pod {pod_name} file {file_name}')
        checksum = write_pod_random_data(pod_name, size_in_mb, file_name)

        logging(f"Storing pod {pod_name} file {file_name} checksum = {checksum}")

        volume_name = get_volume_name_by_pod(pod_name)
        self.volume.set_data_checksum(volume_name, file_name, checksum)
        self.volume.set_last_data_checksum(volume_name, checksum)

    def write_workload_pod_large_data(self, workload_name, size_in_gb, file_name):
        pod_name = get_workload_pod_names(workload_name)[0]

        logging(f'Writing {size_in_gb} GB large data to pod {pod_name} file {file_name}')
        checksum = write_pod_large_data(pod_name, size_in_gb, file_name)

        logging(f"Storing pod {pod_name} file {file_name} checksum = {checksum}")

        volume_name = get_volume_name_by_pod(pod_name)
        self.volume.set_data_checksum(volume_name, file_name, checksum)
        self.volume.set_last_data_checksum(volume_name, checksum)

    def check_workload_pod_data_checksum(self, workload_name, file_name, expected_checksum=""):
        pod_name = get_workload_pod_names(workload_name)[0]
        volume_name = get_volume_name_by_pod(pod_name)
        if not expected_checksum:
            expected_checksum = self.volume.get_data_checksum(volume_name, file_name)

        logging(f'Checking checksum for file {file_name} in workload {workload_name}')
        check_workload_pod_data_checksum(expected_checksum, workload_name, file_name)

    def keep_writing_workload_pod_data(self, workload_name):
        pod_name = get_workload_pod_names(workload_name)[0]

        logging(f'Keep writing data to pod {pod_name}')
        keep_writing_pod_data(pod_name)

    def run_commands_workload_pod(self, workload_name, commands):
        pod_name = get_workload_pod_names(workload_name)[0]
        logging(f'Running commands {commands} in pod {pod_name}')
        run_commands_in_pod(pod_name, commands)

    def wait_for_workload_pods_container_creating(self, workload_name, namespace="default"):
        logging(f'Waiting for {namespace} workload {workload_name} pods container creating')
        wait_for_workload_pods_container_creating(workload_name, namespace=namespace)

    def wait_for_workload_pods_running(self, workload_name, namespace="default"):
        logging(f'Waiting for {namespace} workload {workload_name} pods running')
        wait_for_workload_pods_running(workload_name, namespace=namespace)

    def wait_for_workloads_pods_running(self, workload_names, namespace="default"):
        logging(f'Waiting for {namespace} workloads {workload_names} pods running')
        with multiprocessing.Pool(processes=len(workload_names)) as pool:
            pool.starmap(wait_for_workload_pods_running, [(name, namespace) for name in workload_names])

        pool.join()

    async def wait_for_workloads_pods_stably_running(self, workloads, namespace="default"):
        logging(f'Waiting for workloads {workloads} pods stable')

        async def wait_for_workloads_tasks():
            tasks = []
            for workload_name in workloads:
                tasks.append(
                    asyncio.create_task(wait_for_workload_pods_stable(workload_name, namespace=namespace), name=workload_name)
                )

            done, pending = await asyncio.wait(tasks, return_when=asyncio.ALL_COMPLETED)
            for task in done:
                if task.exception():
                    assert False, task.exception()
            logging(f"All workloads {workloads} pods are stably running now")

        await wait_for_workloads_tasks()

    async def wait_for_workload_pods_stable(self, workload_name, namespace="default"):
        logging(f'Waiting for {namespace} workload {workload_name} pod stable')
        await wait_for_workload_pods_stable(workload_name, namespace=namespace)

    def wait_for_workload_volume_healthy(self, workload_name):
        volume_name = get_workload_volume_name(workload_name)

        logging(f'Waiting for workload {workload_name} volume {volume_name} to be healthy')
        self.volume.wait_for_volume_healthy(volume_name)

    def wait_for_workload_volume_attached(self, workload_name):
        volume_name = get_workload_volume_name(workload_name)

        logging(f'Waiting for workload {workload_name} volume {volume_name} to be attached')
        self.volume.wait_for_volume_attached(volume_name)

    def wait_for_workload_volume_detached(self, workload_name):
        volume_name = get_workload_volume_name(workload_name)

        logging(f'Waiting for {workload_name} volume {volume_name} to be detached')
        self.volume.wait_for_volume_detached(volume_name)

    def expand_workload_claim_size(self, workload_name, size_in_byte, claim_index=0, skip_retry=False):
        claim_name = get_workload_persistent_volume_claim_name(workload_name, index=claim_index)
        current_size = self.persistentvolumeclaim.get(claim_name).spec.resources.requests['storage']
        current_size_byte = convert_size_to_bytes(current_size)

        logging(f'Expanding {workload_name} persistentvolumeclaim {claim_name} from {current_size_byte} to {size_in_byte}')
        self.persistentvolumeclaim.expand(claim_name, size_in_byte, skip_retry=skip_retry)

    def expand_workload_claim_size_with_additional_bytes(self, workload_name, size_in_byte, claim_index=0, skip_retry=False):
        claim_name = get_workload_persistent_volume_claim_name(workload_name, index=claim_index)
        current_size = self.persistentvolumeclaim.get(claim_name).spec.resources.requests['storage']
        current_size_byte = convert_size_to_bytes(current_size)

        logging(f'Expanding {workload_name} persistentvolumeclaim {claim_name} current size {current_size_byte} with additional {size_in_byte}')
        self.persistentvolumeclaim.expand_with_additional_bytes(claim_name, size_in_byte, skip_retry=skip_retry)

    def wait_for_workload_claim_size_expanded(self, workload_name, claim_index=0):
        claim_name = get_workload_persistent_volume_claim_name(workload_name, index=claim_index)
        expanded_size = self.persistentvolumeclaim.get_annotation_value(claim_name, ANNOT_EXPANDED_SIZE)
        volume_name = self.persistentvolumeclaim.get_volume_name(claim_name)

        self.volume.wait_for_volume_attached(volume_name)
        logging(f'Waiting for {workload_name} volume {volume_name} to expand to {expanded_size}')
        self.volume.wait_for_volume_expand_to_size(volume_name, expanded_size)

    def wait_for_pod_kept_in_state(self, workload_name, expect_state, namespace="default"):
        assert expect_state in ["Terminating", "ContainerCreating", "Running", "CrashLoopBackOff"], f"Unknown expected pod state: {expect_state}: "
        return wait_for_workload_pod_kept_in_state(workload_name, expect_state, namespace=namespace)

    def get_pod_node(self, pod):
        return get_pod_node(pod)

    def is_workloads_pods_has_annotations(self, workload_names, annotation_key, namespace=constant.LONGHORN_NAMESPACE):
        for workload_name in workload_names:

            label_selector = ""
            if workload_name == "longhorn-share-manager":
                label_selector = f"{LABEL_LONGHORN_COMPONENT}=share-manager"

            if not is_workload_pods_has_annotations(workload_name, annotation_key, namespace=namespace, label_selector=label_selector):
                return False
        return True

    def is_workloads_pods_has_cni_interface(self, workload_names, interface_name, namespace=constant.LONGHORN_NAMESPACE):
        for workload_name in workload_names:

            label_selector = ""
            if workload_name == "longhorn-share-manager":
                label_selector = f"{LABEL_LONGHORN_COMPONENT}=share-manager"

            if not is_workload_pods_has_cni_interface(workload_name, interface_name, namespace=namespace, label_selector=label_selector):
                return False
        return True

    def trim_workload_volume_filesystem(self, workload_name, is_expect_fail=False):
        volume_name = get_workload_volume_name(workload_name)
        self.volume.trim_filesystem(volume_name, is_expect_fail=is_expect_fail)

    def check_workload_pod_did_not_restart(self, workload_name):
        pod_name = get_workload_pod_names(workload_name)[0]
        logging(f"Checking workload {workload_name} pod {pod_name} did not restart")
        check_pod_did_not_restart(pod_name)

    def get_workload_pod_uids(self, workload_name):
        pod_list = get_workload_pods(workload_name)
        return {pod.metadata.name: pod.metadata.uid for pod in pod_list}

    def check_pod_not_restart_after_specific_time(self, namespace, label, time):        
        pods = list_namespaced_pod(namespace, label)

        if time.tzinfo is None:
            time = time.replace(tzinfo=timezone.utc)

        for pod in pods:
            creation_time = pod.metadata.creation_timestamp
            logging(f"Comparing pod creation: {creation_time} < {time}")
            assert creation_time < time, f"{pod.metadata.name} restarted after test started"

    def wait_for_filesystem_size_in_workload(self, workload_name, expected_size_in_bytes):
        """
        Wait for the filesystem in the workload pod to reflect the expanded size.
        This accounts for filesystem overhead - the actual filesystem size will be
        smaller than the PVC size.
        
        Args:
            workload_name: Name of the workload
            expected_size_in_bytes: Expected filesystem size in bytes (as string)
        """
        from utility.utility import get_retry_count_and_interval
        from workload.workload import get_workload_pod_names
        import time
        
        retry_count, retry_interval = get_retry_count_and_interval()
        pod_names = get_workload_pod_names(workload_name)
        
        if not pod_names:
            assert False, f"No pods found for workload {workload_name}"
        
        pod_name = pod_names[0]
        
        # Convert expected size to an approximate minimum filesystem size
        # Accounting for ~10-15% filesystem overhead
        expected_size_bytes = int(expected_size_in_bytes)
        min_acceptable_size = int(expected_size_bytes * 0.85)  # Allow 15% overhead
        
        for i in range(retry_count):
            logging(f"Waiting for filesystem size in workload {workload_name} to be at least {min_acceptable_size} bytes ... ({i})")
            time.sleep(retry_interval)
            
            # df -P -B1 output format (one filesystem per line):
            # Filesystem 1B-blocks Used Available Use% Mounted
            # /dev/xxx total_size used_size available_size percentage /mount
            # NR==2 skips the header, $2 is the total size in bytes
            cmd = "df -P -B1 /data | awk 'NR==2 {print $2}'"
            try:
                result = run_commands_in_pod(pod_name, cmd)
                actual_size = int(result.strip())
                logging(f"Current filesystem size in workload {workload_name}: {actual_size} bytes, minimum expected: {min_acceptable_size} bytes")
                
                if actual_size >= min_acceptable_size:
                    logging(f"Filesystem size {actual_size} bytes meets requirement (>= {min_acceptable_size} bytes)")
                    return
            except Exception as e:
                logging(f"Error checking filesystem size in workload {workload_name}: {e}")
                continue
        
        assert False, f"Filesystem size in workload {workload_name} did not reach minimum size {min_acceptable_size} bytes"
