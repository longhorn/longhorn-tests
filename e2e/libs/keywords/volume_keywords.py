import asyncio
import time
from node import Node
from node.utility import check_replica_locality

from utility.constant import ANNOT_CHECKSUM
from utility.constant import LABEL_TEST
from utility.constant import LABEL_TEST_VALUE
from utility.utility import logging
from utility.utility import get_retry_count_and_interval
from volume import Volume


class volume_keywords:

    def __init__(self):
        self.node = Node()
        self.volume = Volume()

    def cleanup_volumes(self):
        volumes = self.volume.list(label_selector=f"{LABEL_TEST}={LABEL_TEST_VALUE}")

        logging(f'Cleaning up {len(volumes["items"])} volumes')
        for volume in volumes['items']:
            self.delete_volume(volume['metadata']['name'])

    def create_volume(self, volume_name, size, replica_count, frontend="blockdev", migratable=False, access_mode="RWO"):
        logging(f'Creating volume {volume_name}')
        self.volume.create(volume_name, size, replica_count, frontend, migratable, access_mode)

    def delete_volume(self, volume_name):
        logging(f'Deleting volume {volume_name}')
        self.volume.delete(volume_name)

    def attach_volume(self, volume_name, node_name=None):
        if not node_name:
            node_name = self.node.get_node_by_index(0)
        logging(f'Attaching volume {volume_name} to node {node_name}')
        self.volume.attach(volume_name, node_name)

    def detach_volume(self, volume_name, node_name=None):
        if not node_name:
            node_name = self.node.get_node_by_index(0)
        logging(f'Detaching volume {volume_name} from node {node_name}')
        self.volume.detach(volume_name, node_name)

    def list_volumes(self):
        logging(f'Listing volumes')
        return self.volume.list_names()

    def wait_for_volume_expand_to_size(self, volume_name, size):
        logging(f'Waiting for volume {volume_name} expand to {size}')
        return self.volume.wait_for_volume_expand_to_size(volume_name, size)

    def get_replica_node_ids(self, volume_name):
        node_ids = []
        node_ids.extend(self.get_node_ids_by_replica_locality(volume_name, "volume node"))
        node_ids.extend(self.get_node_ids_by_replica_locality(volume_name, "replica node"))
        node_ids.extend(self.get_node_ids_by_replica_locality(volume_name, "test pod node"))
        return node_ids

    def get_replica_node(self, volume_name):
        return self.get_node_id_by_replica_locality(volume_name, "replica node")

    def get_volume_node(self, volume_name):
        return self.get_node_id_by_replica_locality(volume_name, "volume node")

    def get_node_id_by_replica_locality(self, volume_name, replica_locality):
        return self.get_node_ids_by_replica_locality(volume_name, replica_locality)[0]

    def get_node_ids_by_replica_locality(self, volume_name, replica_locality):
        check_replica_locality(replica_locality)

        if replica_locality == "volume node":
            volume = self.volume.get(volume_name)
            return [volume['spec']['nodeID']]

        worker_nodes = self.node.list_node_names_by_role("worker")
        volume_node = self.get_node_id_by_replica_locality(volume_name, "volume node")
        replica_nodes = [node for node in worker_nodes if node != volume_node]
        test_pod_node = self.node.get_test_pod_running_node()

        if replica_locality == "test pod node":
            if test_pod_node in replica_nodes:
                return [test_pod_node]

        elif replica_locality == "replica node":
            return [node for node in replica_nodes if node != test_pod_node]

        else:
            raise ValueError(f"Unknown replica locality {replica_locality}")

        raise Exception(f"Failed to get node ID of the replica on {replica_locality}")

    def write_volume_random_data(self, volume_name, size_in_mb):
        logging(f'Writing {size_in_mb} MB random data to volume {volume_name}')
        checksum = self.volume.write_random_data(volume_name, size_in_mb)

        self.volume.set_annotation(volume_name, ANNOT_CHECKSUM, checksum)

    def keep_writing_data(self, volume_name):
        logging(f'Keep writing data to volume {volume_name}')
        self.volume.keep_writing_data(volume_name)

    def check_data_checksum(self, volume_name):
        checksum = self.volume.get_annotation_value(volume_name, ANNOT_CHECKSUM)

        logging(f"Checking volume {volume_name} data checksum is {checksum}")
        self.volume.check_data_checksum(volume_name, checksum)

    def delete_replica(self, volume_name, replica_node):
        if str(replica_node).isdigit():
            replica_node = self.node.get_node_by_index(replica_node)

        logging(f"Deleting volume {volume_name}'s replica on node {replica_node}")
        self.volume.delete_replica(volume_name, replica_node)

    def delete_replica_on_node(self, volume_name, replica_locality):
        check_replica_locality(replica_locality)

        node_id = self.get_node_id_by_replica_locality(volume_name, replica_locality)

        logging(f"Deleting volume {volume_name}'s replica on node {node_id}")
        self.volume.delete_replica(volume_name, node_id)

    def set_annotation(self, volume_name, annotation_key, annotation_value):
        self.volume.set_annotation(volume_name, annotation_key, annotation_value)

    async def wait_for_replica_rebuilding_start(self, volume_name, replica_node):
        if str(replica_node).isdigit():
            replica_node = self.node.get_node_by_index(replica_node)

        logging(f"Waiting for volume {volume_name}'s replica on node {replica_node} rebuilding started")
        await self.volume.wait_for_replica_rebuilding_start(
            volume_name,
            replica_node
        )

    async def wait_for_replica_rebuilding_to_start_on_node(self, volume_name, replica_locality):
        check_replica_locality(replica_locality)

        node_id = self.get_node_id_by_replica_locality(volume_name, replica_locality)

        logging(f"Waiting for volume {volume_name}'s replica on node {node_id} rebuilding started")
        await self.volume.wait_for_replica_rebuilding_start(volume_name, node_id)

    def wait_for_replica_rebuilding_complete(self, volume_name, replica_node):
        if str(replica_node).isdigit():
            replica_node = self.node.get_node_by_index(replica_node)

        logging(f"Waiting for volume {volume_name}'s replica on node {replica_node} rebuilding completed")
        self.volume.wait_for_replica_rebuilding_complete(
            volume_name,
            replica_node
        )

    def wait_for_replica_rebuilding_to_complete_on_node(self, volume_name, replica_locality):
        check_replica_locality(replica_locality)

        node_id = self.get_node_id_by_replica_locality(volume_name, replica_locality)

        logging(f"Waiting for volume {volume_name}'s replica on node {node_id} rebuilding completed")
        self.volume.wait_for_replica_rebuilding_complete(volume_name, node_id)

    def wait_for_replica_rebuilding_to_complete(self, volume_name):
        for node_id in self.get_replica_node_ids(volume_name):
            logging(f"Waiting for volume {volume_name}'s replica on node {node_id} rebuilding completed")
            self.volume.wait_for_replica_rebuilding_complete(volume_name, node_id)

    async def only_one_replica_rebuilding_will_start_at_a_time_on_node(self, volume_name_0, volume_name_1, replica_locality):

        node_id = self.get_node_id_by_replica_locality(volume_name_0, replica_locality)

        first_replica_rebuilding = None
        not_start_replica_rebuilding = None

        async def find_first_replica_rebuilding():
            tasks = [
                asyncio.create_task(self.volume.wait_for_replica_rebuilding_start(volume_name_0, node_id), name=volume_name_0),
                asyncio.create_task(self.volume.wait_for_replica_rebuilding_start(volume_name_1, node_id), name=volume_name_1)
            ]

            done, pending = await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)
            for pending_task in pending:
                pending_task.cancel()
            return done.pop().get_name(), pending.pop().get_name()

        first_replica_rebuilding, not_start_replica_rebuilding = await find_first_replica_rebuilding()
        logging(f"Observed {first_replica_rebuilding} started replica rebuilding first")

        while self.volume.is_replica_rebuilding_in_progress(first_replica_rebuilding, node_id):
            logging(f"Checking volume {not_start_replica_rebuilding} replica rebuilding won't start \
                if volume {first_replica_rebuilding} replica rebuilding is still in progress")
            assert not self.volume.is_replica_rebuilding_in_progress(not_start_replica_rebuilding, node_id)
            time.sleep(1)

    async def both_replica_rebuildings_will_start_at_the_same_time_on_node(self, volume_name_0, volume_name_1, replica_locality):

        node_id = self.get_node_id_by_replica_locality(volume_name_0, replica_locality)

        async def wait_for_both_replica_rebuildings():
            tasks = [
                asyncio.create_task(self.volume.wait_for_replica_rebuilding_start(volume_name_0, node_id), name=volume_name_0),
                asyncio.create_task(self.volume.wait_for_replica_rebuilding_start(volume_name_1, node_id), name=volume_name_1)
            ]

            done, pending = await asyncio.wait(tasks, return_when=asyncio.ALL_COMPLETED)
            logging(f"Observed {done.pop().get_name()} and {done.pop().get_name()} started replica rebuilding first")

        await wait_for_both_replica_rebuildings()

        assert self.volume.is_replica_rebuilding_in_progress(volume_name_0, node_id) and self.volume.is_replica_rebuilding_in_progress(volume_name_1, node_id), \
            f"Expect {volume_name_0} and {volume_name_1} replica rebuilding at the same time"

    def crash_replica_processes(self, volume_name):
        self.volume.crash_replica_processes(volume_name)

    def wait_for_replica_rebuilding_to_stop_on_node(self, volume_name, replica_locality):
        node_id = self.get_node_id_by_replica_locality(volume_name, replica_locality)
        retry_count, retry_interval = get_retry_count_and_interval()
        for i in range(retry_count):
            if not self.volume.is_replica_rebuilding_in_progress(volume_name, node_id):
                break
            time.sleep(retry_interval)

    def wait_for_volume_attached(self, volume_name):
        logging(f'Waiting for volume {volume_name} to be attached')
        self.volume.wait_for_volume_attached(volume_name)

    def wait_for_volume_detached(self, volume_name):
        logging(f'Waiting for volume {volume_name} to be detached')
        self.volume.wait_for_volume_detached(volume_name)

    def wait_for_volume_healthy(self, volume_name):
        logging(f'Waiting for volume {volume_name} to be healthy')
        self.volume.wait_for_volume_healthy(volume_name)

    def wait_for_volume_migration_ready(self, volume_name):
        logging(f'Waiting for volume {volume_name} migration to be ready')
        self.volume.wait_for_volume_migration_ready(volume_name)

    def wait_for_volume_migration_completed(self, volume_name, node_name):
        logging(f'Waiting for volume {volume_name} migration to node {node_name} completed')
        self.volume.wait_for_volume_migration_completed(volume_name, node_name)

    def validate_volume_replicas_anti_affinity(self, volume_name):
        self.volume.validate_volume_replicas_anti_affinity(volume_name)

    def wait_for_volume_degraded(self, volume_name):
        self.volume.wait_for_volume_degraded(volume_name)

    def wait_for_volume_unknown(self, volume_name):
        self.volume.wait_for_volume_unknown(volume_name)
