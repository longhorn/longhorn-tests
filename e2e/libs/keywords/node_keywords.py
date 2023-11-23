from robot.libraries.BuiltIn import BuiltIn

from instancemanager.utility import wait_for_all_instance_manager_running

from node import Node
from node.utility import get_node_by_index


class node_keywords:

    def __init__(self):
        self.node = Node()

    def reboot_volume_node(self, volume_name):
        volume_keywords = BuiltIn().get_library_instance('volume_keywords')
        volume_node = volume_keywords.get_replica_node_attached_to_volume(volume_name)
        self.node.reboot_node(volume_node)

    def reboot_replica_node(self, volume_name):
        volume_keywords = BuiltIn().get_library_instance('volume_keywords')
        replica_node = volume_keywords.get_replica_node_not_attached_to_volume(volume_name)
        self.node.reboot_node(replica_node)

    def reboot_node_by_index(self, idx, power_off_time_in_min=1):
        node_name = get_node_by_index(idx)
        self.node.reboot_node(node_name, int(power_off_time_in_min) * 60)

    def reboot_all_worker_nodes(self, power_off_time_in_min=1):
        self.node.reboot_all_worker_nodes(int(power_off_time_in_min) * 60)

    def reboot_all_nodes(self):
        self.node.reboot_all_nodes()

    def reboot_node_by_name(self, node_name, power_off_time_in_min=1):
        self.node.reboot_node(node_name, int(power_off_time_in_min) * 60)

    def wait_for_all_instance_manager_running(self):
        wait_for_all_instance_manager_running()
