from node import Node

from utility.utility import logging


class node_keywords:

    def __init__(self):
        self.node = Node()

    def list_node_names_by_role(self, role):
        return self.node.list_node_names_by_role(role)

    def mount_disk(self, disk_name, node_name):
        logging(f"Mount device /dev/longhorn/{disk_name} on node {node_name}")
        return self.node.mount_disk(disk_name, node_name)

    def add_disk(self, disk_name, node_name, type, path):
        logging(f"Adding {type} type disk {disk_name} {path} to node {node_name}")
        disk = {
            f"{disk_name}": {
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

    def set_node(self, node_name, allowScheduling=True, evictionRequested=False):
        logging(f"Setting node {node_name}; scheduling={allowScheduling}; evictionRequested={evictionRequested}")
        self.node.set_node(node_name, allowScheduling, evictionRequested)

    def disable_disk(self, node_name, disk_name):
        self.node.set_disk_scheduling(node_name, disk_name, allowScheduling=False)

    def enable_disk(self, node_name, disk_name):
        self.node.set_disk_scheduling(node_name, disk_name, allowScheduling=True)


    def disable_node_scheduling(self, node_name):
        self.node.set_node_scheduling(node_name, allowScheduling=False)

    def enable_node_scheduling(self, node_name):
        self.node.set_node_scheduling(node_name, allowScheduling=True)

    def reset_node_schedule(self):
        nodes = self.node.list_node_names_by_role("worker")

        for node_name in nodes:
            self.enable_node_scheduling(node_name)

    def check_node_is_not_schedulable(self, node_name):
        self.node.check_node_schedulable(node_name, schedulable="False")

    def is_disk_in_pressure(self, node_name, disk_name):
        return self.node.is_disk_in_pressure(node_name, disk_name)

    def wait_for_disk_in_pressure(self, node_name, disk_name):
        self.node.wait_for_disk_in_pressure(node_name, disk_name)

    def wait_for_disk_not_in_pressure(self, node_name, disk_name):
        self.node.wait_for_disk_not_in_pressure(node_name, disk_name)

    def get_disk_uuid(self, node_name, disk_name):
        return self.node.get_disk_uuid(node_name, disk_name)

    def list_dm_devices_on_node(self, node_name):
        return self.node.list_dm_devices(node_name)

    def list_volume_devices_on_node(self, node_name):
        return self.node.list_volume_devices(node_name)
