from utility.utility import get_test_pod_running_node
from robot.libraries.BuiltIn import BuiltIn
from node import Node
import logging

class node_keywords:

    def __init__(self):
        logging.warn("initialize node_keywords class")
        self.node = Node()

    def reboot_volume_node(self, volume_name):
        test_pod_running_node = get_test_pod_running_node()
        volume_keywords = BuiltIn().get_library_instance('volume_keywords')
        volume_node = volume_keywords.get_volume_node(volume_name)
        self.node.reboot_node(test_pod_running_node, volume_node)

    def reboot_replica_node(self, volume_name):
        test_pod_running_node = get_test_pod_running_node()
        volume_keywords = BuiltIn().get_library_instance('volume_keywords')
        replica_node = volume_keywords.get_replica_node(volume_name)
        self.node.reboot_node(test_pod_running_node, replica_node)

    def restart_all_nodes(self):
        self.node.restart_all_nodes()
