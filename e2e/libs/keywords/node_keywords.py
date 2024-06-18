from node import Node
from utility.utility import logging

class node_keywords:

    def __init__(self):
        self.node = Node()

    def list_node_names_by_role(self, role):
        return self.node.list_node_names_by_role(role)

    def add_disk(self, node_name, type, path):
        logging(f"Adding {type} type disk {path} to node {node_name}")
        disk = {
            f"{type}-disk": {
                "diskType": type,
                "path": path,
                "allowScheduling": True
            }
        }
        self.node.add_disk(node_name, disk)

    def cleanup_disks(self):
        nodes = self.node.list_node_names_by_role("worker")
        for node_name in nodes:
            logging(f"Resetting node {node_name} disks to default")
            self.node.reset_disks(node_name)

    def disable_default_disk(self, node_name):
        self.node.set_default_disk_scheduling(node_name, allowScheduling=False)

    def enable_default_disk(self, node_name):
        self.node.set_default_disk_scheduling(node_name, allowScheduling=True)

    def disable_node_scheduling(self, node_name):
        self.node.set_node_scheduling(node_name, allowScheduling=False)

    def enable_node_scheduling(self, node_name):
        self.node.set_node_scheduling(node_name, allowScheduling=True)

    def reset_node_schedule(self):
        nodes = self.node.list_node_names_by_role("worker")
        for node_name in nodes:
            self.enable_node_scheduling(node_name)
