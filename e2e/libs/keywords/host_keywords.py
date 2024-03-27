from robot.libraries.BuiltIn import BuiltIn

from host import Host
from host.constant import NODE_REBOOT_DOWN_TIME_SECOND

from node import Node

from utility.utility import logging


class host_keywords:

    def __init__(self):
        #TODO
        # call BuiltIn().get_library_instance() in keyword init function
        # could fail because the keyword instance could not be created yet
        # whether it will fail or not will depend on import orders.
        self.volume_keywords = BuiltIn().get_library_instance('volume_keywords')

        self.host = Host()
        self.node = Node()

    def reboot_volume_node(self, volume_name):
        node_id = self.volume_keywords.get_node_id_by_replica_locality(volume_name, "volume node")

        logging(f'Rebooting volume {volume_name} node {node_id} with downtime {NODE_REBOOT_DOWN_TIME_SECOND} seconds')
        self.host.reboot_node(node_id)

    def reboot_replica_node(self, volume_name):
        node_id = self.volume_keywords.get_node_id_by_replica_locality(volume_name, "replica node")

        logging(f'Rebooting volume {volume_name} node {node_id} with downtime {NODE_REBOOT_DOWN_TIME_SECOND} seconds')
        self.host.reboot_node(node_id)

    def reboot_node_by_index(self, idx, power_off_time_in_min=1):
        node_name = self.node.get_node_by_index(idx)
        reboot_down_time_min = int(power_off_time_in_min) * 60

        logging(f'Rebooting node {node_name} with downtime {reboot_down_time_min} minutes')
        self.host.reboot_node(node_name, reboot_down_time_min)

    def reboot_all_worker_nodes(self, power_off_time_in_min=1):
        reboot_down_time_min = int(power_off_time_in_min) * 60

        logging(f'Rebooting all worker nodes with downtime {reboot_down_time_min} minutes')
        self.host.reboot_all_worker_nodes(reboot_down_time_min)

    def reboot_all_nodes(self):
        logging(f'Rebooting all nodes with downtime {NODE_REBOOT_DOWN_TIME_SECOND} seconds')
        self.host.reboot_all_nodes()

    def reboot_node_by_name(self, node_name, downtime_in_min=1):
        reboot_down_time_min = int(downtime_in_min) * 60

        logging(f'Rebooting node {node_name} with downtime {reboot_down_time_min} minutes')
        self.host.reboot_node(node_name, reboot_down_time_min)
