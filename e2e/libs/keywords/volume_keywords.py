from utility.utility import get_test_case_namespace, generate_volume_name
from utility.utility import get_node, list_nodes
from utility.utility import get_test_pod_running_node, get_test_pod_not_running_node
from robot.libraries.BuiltIn import BuiltIn
from node_exec import NodeExec
from volume import Volume
import logging

class volume_keywords:

    def __init__(self):
        #TODO
        #test_name = BuiltIn().get_variable_value("${TEST NAME}")
        self.node_exec = NodeExec("default")
        self.volume = Volume(self.node_exec)


    def create_volume(self, size, replica_count):
        volume_name = generate_volume_name()
        self.volume.create(volume_name, size, replica_count)
        logging.info(f'==> create volume {volume_name}')
        return volume_name


    def attach_volume(self, volume_name):
        attach_node = get_test_pod_not_running_node()
        logging.info(f'==> attach volume {volume_name} to {attach_node}')
        self.volume.attach(volume_name, attach_node)


    def get_volume_node(self, volume_name):
        volume = self.volume.get(volume_name)
        print(volume)
        return volume['spec']['nodeID']
        # return volume.controllers[0].hostId


    def get_replica_node(self, volume_name):
        nodes = list_nodes()
        volume_node = self.get_volume_node(volume_name)
        test_pod_running_node = get_test_pod_running_node()
        for node in nodes:
            if node != volume_node and node != test_pod_running_node:
                return node


    def write_volume_random_data(self, volume_name, size_in_mb):
        print('write_volume_random_data')
        return self.volume.write_random_data(volume_name, size_in_mb)


    def check_data(self, volume_name, checksum):
        print(f"check volume {volume_name} data with checksum {checksum}")
        self.volume.check_data(volume_name, checksum)


    def delete_replica(self, volume_name, replica_node):
        if str(replica_node).isdigit():
            replica_node = get_node(replica_node)
        logging.info(f"==> delete volume {volume_name}'s replica\
                       on node {replica_node}")
        self.volume.delete_replica(volume_name, replica_node)


    def wait_for_replica_rebuilding_start(self, volume_name, replica_node):
        if str(replica_node).isdigit():
            replica_node = get_node(replica_node)
        logging.info(f"==> wait for volume {volume_name}'s replica\
                       on node {replica_node} rebuilding started")
        self.volume.wait_for_replica_rebuilding_start(
            volume_name,
            replica_node
        )


    def wait_for_replica_rebuilding_complete(self, volume_name, replica_node):
        if str(replica_node).isdigit():
            replica_node = get_node(replica_node)
        logging.info(f"==> wait for volume {volume_name}'s replica\
                       on node {replica_node} rebuilding completed")
        self.volume.wait_for_replica_rebuilding_complete(
            volume_name,
            replica_node
        )

    def cleanup_resources(self):
        logging.info('cleaning up resources')
        self.node_exec.cleanup()