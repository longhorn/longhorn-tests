from utility.utility import get_test_pod_running_node
from robot.libraries.BuiltIn import BuiltIn
from node import Node
import logging

class node_keywords:

    def __init__(self):
        self.node = Node()

    def reboot_volume_attached_node(self, volume_name):
        test_pod_running_node = get_test_pod_running_node()
        volume_keywords = BuiltIn().get_library_instance('volume_keywords')
        volume_attached_node = volume_keywords.get_volume_attached_node(volume_name)
        self.node.reboot_node(test_pod_running_node, volume_attached_node)

    def reboot_node_with_replica(self, volume_name):
        test_pod_running_node = get_test_pod_running_node()
        volume_keywords = BuiltIn().get_library_instance('volume_keywords')
        volume_not_attached_node = volume_keywords.get_volume_not_attached_node(volume_name)
        self.node.reboot_node(test_pod_running_node, volume_not_attached_node)
