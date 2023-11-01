from node.utility import get_node_by_index
from node.utility import list_node_names_by_role

from utility.utility import generate_volume_name
from utility.utility import get_test_pod_not_running_node
from utility.utility import get_test_pod_running_node
from utility.utility import logging

from volume import Volume

from volume.constant import MEBIBYTE


class volume_keywords:

    def __init__(self):
        self.volume = Volume()


    def create_volume(self, size, replica_count):
        volume_name = generate_volume_name()
        logging(f'Creating volume {volume_name}')
        self.volume.create(volume_name, size, replica_count)
        return volume_name


    def attach_volume(self, volume_name):
        attach_node = get_test_pod_not_running_node()
        logging(f'Attaching volume {volume_name} to {attach_node}')
        self.volume.attach(volume_name, attach_node)


    def detach_volume(self, volume_name):
        logging(f'Detaching volume {volume_name}')
        self.volume.detach(volume_name)


    def wait_for_volume_expand_to_size(self, volume_name, size):
        logging(f'Waiting for volume {volume_name} expand to {size}')
        return self.volume.wait_for_volume_expand_to_size(volume_name, size)


    def get_volume_node(self, volume_name):
        volume = self.volume.get(volume_name)
        return volume['spec']['nodeID']


    def get_replica_node(self, volume_name):
        worker_nodes = list_node_names_by_role("worker")
        volume_node = self.get_volume_node(volume_name)
        test_pod_running_node = get_test_pod_running_node()
        for worker_node in worker_nodes:
            if worker_node != volume_node and worker_node != test_pod_running_node:
                return worker_node


    def write_volume_random_data(self, volume_name, size_in_mb):
        return self.volume.write_random_data(volume_name, size_in_mb)


    def keep_writing_data(self, volume_name):
        self.volume.keep_writing_data(volume_name)


    def check_data_checksum(self, volume_name, checksum):
        logging(f"Checking volume {volume_name} data with checksum {checksum}")
        self.volume.check_data_checksum(volume_name, checksum)


    def delete_replica(self, volume_name, replica_node):
        if str(replica_node).isdigit():
            replica_node = get_node_by_index(replica_node)
        logging(f"Deleting volume {volume_name}'s replica on node {replica_node}")
        self.volume.delete_replica(volume_name, replica_node)


    def wait_for_replica_rebuilding_start(self, volume_name, replica_node):
        if str(replica_node).isdigit():
            replica_node = get_node_by_index(replica_node)
        logging(f"Waiting for volume {volume_name}'s replica on node {replica_node} rebuilding started")
        self.volume.wait_for_replica_rebuilding_start(
            volume_name,
            replica_node
        )


    def wait_for_replica_rebuilding_complete(self, volume_name, replica_node):
        if str(replica_node).isdigit():
            replica_node = get_node_by_index(replica_node)
        logging(f"Waiting for volume {volume_name}'s replica on node {replica_node} rebuilding completed")
        self.volume.wait_for_replica_rebuilding_complete(
            volume_name,
            replica_node
        )

    def wait_for_volume_attached(self, volume_name):
        self.volume.wait_for_volume_attached(volume_name)

    def wait_for_volume_detached(self, volume_name):
        self.volume.wait_for_volume_detached(volume_name)

    def wait_for_volume_healthy(self, volume_name):
        self.volume.wait_for_volume_healthy(volume_name)

    def cleanup_volumes(self, volume_names):
        self.volume.cleanup(volume_names)