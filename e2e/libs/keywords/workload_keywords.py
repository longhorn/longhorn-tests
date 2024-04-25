import multiprocessing
import asyncio

from persistentvolumeclaim import PersistentVolumeClaim

from workload.pod import get_volume_name_by_pod
from workload.workload import check_pod_data_checksum
from workload.workload import get_workload_pod_names
from workload.workload import get_workload_persistent_volume_claim_name
from workload.workload import get_workload_volume_name
from workload.workload import keep_writing_pod_data
from workload.workload import write_pod_random_data
from workload.workload import wait_for_workload_pods_running
from workload.workload import wait_for_workload_pods_stable
from workload.workload import wait_for_workload_pod_kept_in_state
from workload.workload import get_pod_node

from utility.constant import ANNOT_CHECKSUM
from utility.constant import ANNOT_EXPANDED_SIZE
from utility.utility import logging
from node.utility import check_replica_locality
from node.node import Node

from volume import Volume
from volume.constant import MEBIBYTE


class workload_keywords:

    def __init__(self):
        self.persistentvolumeclaim = PersistentVolumeClaim()
        self.volume = Volume()

    def check_pod_data_checksum(self, expected_checksum, pod_name, file_name):
        logging(f'Checking checksum for file {file_name} in pod {pod_name}')
        check_pod_data_checksum(expected_checksum, pod_name, file_name)

    def get_workload_pod_name(self, workload_name):
        return get_workload_pod_names(workload_name)[0]

    def get_workload_persistent_volume_claim_name(self, workload_name):
        return get_workload_persistent_volume_claim_name(workload_name)

    def get_workload_volume_name(self, workload_name):
        return get_workload_volume_name(workload_name)

    def write_workload_pod_random_data(self, workload_name, size_in_mb, file_name):
        pod_name = get_workload_pod_names(workload_name)[0]

        logging(f'Writing {size_in_mb} MB random data to pod {pod_name}')
        checksum = write_pod_random_data(pod_name, size_in_mb, file_name)

        volume_name = get_volume_name_by_pod(pod_name)
        self.volume.set_annotation(volume_name, ANNOT_CHECKSUM, checksum)

    def check_workload_pod_data_checksum(self, workload_name, file_name):
        pod_name = get_workload_pod_names(workload_name)[0]
        volume_name = get_volume_name_by_pod(pod_name)
        expected_checksum = self.volume.get_annotation_value(volume_name, ANNOT_CHECKSUM)

        logging(f'Checking checksum for file {file_name} in pod {pod_name}')
        check_pod_data_checksum(expected_checksum, pod_name, file_name)

    def keep_writing_workload_pod_data(self, workload_name):
        pod_name = get_workload_pod_names(workload_name)[0]

        logging(f'Keep writing data to pod {pod_name}')
        keep_writing_pod_data(pod_name)

    def wait_for_workload_pods_running(self, workload_name, namespace="default"):
        logging(f'Waiting for {namespace} workload {workload_name} pods running')
        wait_for_workload_pods_running(workload_name, namespace=namespace)

    def wait_for_workloads_pods_running(self, workload_names, namespace="default"):
        logging(f'Waiting for {namespace} workloads {workload_names} pods running')
        with multiprocessing.Pool(processes=len(workload_names)) as pool:
            pool.starmap(wait_for_workload_pods_running, [(name, namespace) for name in workload_names])

        pool.join()

    async def wait_for_workloads_pods_stably_running(self, workloads):
        logging(f'Waiting for workloads {workloads} pods stable')

        async def wait_for_workloads_tasks():
            tasks = []
            for workload_name in workloads:
                tasks.append(
                    asyncio.create_task(wait_for_workload_pods_stable(workload_name, namespace="default"), name=workload_name)
                )

            done, pending = await asyncio.wait(tasks, return_when=asyncio.ALL_COMPLETED)
            logging(f"All workloads {workloads} pods are stably running now")

        await wait_for_workloads_tasks()

    async def wait_for_workload_pods_stable(self, workload_name, namespace="default"):
        logging(f'Waiting for {namespace} workload {workload_name} pod stable')
        await wait_for_workload_pods_stable(workload_name, namespace=namespace)

    def wait_for_workload_volume_healthy(self, workload_name):
        volume_name = get_workload_volume_name(workload_name)

        logging(f'Waiting for workload {workload_name} volume {volume_name} to be healthy')
        self.volume.wait_for_volume_healthy(volume_name)

    def wait_for_workload_volume_detached(self, workload_name):
        volume_name = get_workload_volume_name(workload_name)

        logging(f'Waiting for {workload_name} volume {volume_name} to be detached')
        self.volume.wait_for_volume_detached(volume_name)

    def expand_workload_claim_size_by_mib(self, workload_name, size_in_mib, claim_index=0):
        claim_name = get_workload_persistent_volume_claim_name(workload_name, index=claim_index)
        size_in_byte = int(size_in_mib) * MEBIBYTE

        logging(f'Expanding {workload_name} persistentvolumeclaim {claim_name} by {size_in_mib} MiB')
        self.persistentvolumeclaim.expand(claim_name, size_in_byte)

    def wait_for_workload_claim_size_expanded(self, workload_name, claim_index=0):
        claim_name = get_workload_persistent_volume_claim_name(workload_name, index=claim_index)
        expanded_size = self.persistentvolumeclaim.get_annotation_value(claim_name, ANNOT_EXPANDED_SIZE)
        volume_name = self.persistentvolumeclaim.get_volume_name(claim_name)

        self.volume.wait_for_volume_attached(volume_name)
        logging(f'Waiting for {workload_name} volume {volume_name} to expand to {expanded_size}')
        self.volume.wait_for_volume_expand_to_size(volume_name, expanded_size)
        self.volume.wait_for_volume_detached(volume_name)

    def wait_for_pod_kept_in_state(self, workload_name, expect_state, namespace="default"):
        assert expect_state in ["Terminating", "ContainerCreating", "Running"], f"Unknown expected pod state: {expect_state}: "
        return wait_for_workload_pod_kept_in_state(workload_name, expect_state, namespace=namespace)

    def get_pod_node(self, pod):
        return get_pod_node(pod)
