from utility.utility import get_test_pod_running_node
from utility.utility import get_node
from utility.utility import wait_for_all_instance_manager_running
from robot.libraries.BuiltIn import BuiltIn
from node import Node
import logging

class node_keywords:

    def __init__(self):
        logging.warn("initialize node_keywords class")
        self.node = Node()

    def reboot_volume_node(self, volume_name):
        volume_keywords = BuiltIn().get_library_instance('volume_keywords')
        volume_node = volume_keywords.get_volume_node(volume_name)
        self.node.reboot_node(volume_node)

    def reboot_replica_node(self, volume_name):
        volume_keywords = BuiltIn().get_library_instance('volume_keywords')
        replica_node = volume_keywords.get_replica_node(volume_name)
        self.node.reboot_node(replica_node)

    def power_off_node(self, idx, power_off_time_in_min=1):
        node_name = get_node(idx)
        self.node.reboot_node(node_name, int(power_off_time_in_min) * 60)

    def power_off_all_worker_nodes(self, power_off_time_in_min=1):
        self.node.reboot_all_worker_nodes(int(power_off_time_in_min) * 60)

    def reboot_all_nodes(self):
        self.node.reboot_all_nodes()

    def wait_for_all_instance_manager_running(self):
        wait_for_all_instance_manager_running()
