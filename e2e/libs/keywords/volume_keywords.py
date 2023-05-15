from pathlib import Path
from volume import Volume
from utility import Utility
from node import Node
from node_exec import NodeExec

class volume_keywords:

    ROBOT_LIBRARY_SCOPE = 'TEST'

    def __init__(self):
        Utility().init_k8s_api_client()


    def set_test_name(self, test_name):
        self.namespace = test_name.lower().replace(' ', '-')
        self.node_exec = NodeExec(self.namespace)
        self.volume = Volume(self.node_exec)


    def create_volume(self, size, replica_count):
        print('create_volume')
        volume_name = Utility().generate_volume_name()
        self.volume.create(volume_name, size, replica_count)
        return volume_name


    def attach_volume(self, volume_name, attached_node_index=0):
        print('attach_volume')
        node_name = Node().get_by_index(attached_node_index)
        self.volume.attach(volume_name, node_name)


    def write_volume_random_data(self, volume_name, size_in_mb):
        print('write_volume_random_data')
        return self.volume.write_random_data(volume_name, size_in_mb)


    def check_data(self, volume_name, checksum):
        print(f"check volume {volume_name} data with checksum {checksum}")
        self.volume.check_data(volume_name, checksum)


    def delete_replica(self, volume_name, replica_index):
        replica_node_name = Node().get_by_index(int(replica_index))
        print(f"delete volume {volume_name}'s replica\
                {replica_index} {replica_node_name}")
        self.volume.delete_replica(volume_name, replica_node_name)


    def wait_for_replica_rebuilding_start(self, volume_name, replica_index):
        replica_node_name = Node().get_by_index(int(replica_index))
        print(f"wait for  volume {volume_name}'s replica\
                {replica_index} {replica_node_name} rebuilding started")
        self.volume.wait_for_replica_rebuilding_start(
            volume_name,
            replica_node_name
        )


    def wait_for_replica_rebuilding_complete(self, volume_name, replica_index):
        replica_node_name = Node().get_by_index(int(replica_index))
        print(f"wait for  volume {volume_name}'s replica\
                {replica_index} {replica_node_name} rebuilding completed")
        self.volume.wait_for_replica_rebuilding_complete(
            volume_name,
            replica_node_name
        )


    def cleanup_resources(self):
        print('cleanup_resources')
        self.node_exec.cleanup()
