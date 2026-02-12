from node import Node

from utility.utility import logging
from utility.constant import DISK_UNSCHEDULABLE_KEEP_ROUNDS

class node_keywords:

    def __init__(self):
        self.node = Node()

    def list_node_names_by_role(self, role):
        return self.node.list_node_names_by_role(role)

    def mount_disk(self, disk_name, node_name):
        logging(f"Mount device /dev/longhorn/{disk_name} on node {node_name}")
        return self.node.mount_disk(disk_name, node_name)

    def add_disk(self, disk_name, node_name, type, path, wait=True):
        logging(f"Adding {type} type disk {disk_name} {path} to node {node_name}")
        disk = {
            f"{disk_name}": {
                "diskType": type,
                "path": path,
                "allowScheduling": True
            }
        }
        self.node.add_disk(node_name, disk, wait)

    def cleanup_disks(self, data_engine, default_block_disk_path=None):
        nodes = self.node.list_node_names_by_role("worker")
        for node_name in nodes:
            logging(f"Resetting node {node_name} disks to default")
            self.node.reset_disks(node_name, data_engine, default_block_disk_path)

    def reset_node_disks_tags(self):
        nodes = self.node.list_node_names_by_role("worker")
        for node_name in nodes:
            logging(f"Resetting node {node_name} disks tags")
            self.set_node_disks_tags(node_name)

    def disable_default_disk(self, node_name):
        self.node.set_default_disk_scheduling(node_name, allowScheduling=False)

    def enable_default_disk(self, node_name):
        self.node.set_default_disk_scheduling(node_name, allowScheduling=True)

    def set_node(self, node_name, allowScheduling=True, evictionRequested=False):
        logging(f"Setting node {node_name}; scheduling={allowScheduling}; evictionRequested={evictionRequested}")
        self.node.set_node(node_name, allowScheduling, evictionRequested)

    def set_node_tags(self, node_name, *tags):
        self.node.set_node_tags(node_name, tags)

    def set_node_disks_tags(self, node_name, *tags):
        self.node.set_node_disks_tags(node_name, tags)

    def label_node(self, node_name, label):
        self.node.label_node(node_name, label)

    def cleanup_node_labels(self):
        self.node.cleanup_node_labels()

    def cleanup_node_taints(self):
        self.node.cleanup_node_taints()

    def disable_disk(self, node_name, disk_name, wait=True):
        self.node.set_disk_scheduling(node_name, disk_name, allowScheduling=False, wait=wait)

    def enable_disk(self, node_name, disk_name):
        self.node.set_disk_scheduling(node_name, disk_name, allowScheduling=True)

    def request_eviction_on_default_disk(self, node_name):
        self.node.set_default_disk_eviction_requested(node_name, evictionRequested=True)

    def cancel_eviction_on_default_disk(self, node_name):
        self.node.set_default_disk_eviction_requested(node_name, evictionRequested=False)

    def request_eviction_on_disk(self, node_name, disk_name):
        self.node.set_disk_eviction_requested(node_name, disk_name, evictionRequested=True)

    def cancel_eviction_on_disk(self, node_name, disk_name):
        self.node.set_disk_eviction_requested(node_name, disk_name, evictionRequested=False)

    def disable_node_scheduling(self, node_name):
        self.node.set_node_scheduling(node_name, allowScheduling=False)

    def enable_node_scheduling(self, node_name):
        self.node.set_node_scheduling(node_name, allowScheduling=True)

    def evict_node(self, node_name):
        self.node.evict_node(node_name)

    def unevict_node(self, node_name):
        self.node.unevict_node(node_name)

    def reset_disk_eviction_and_scheduling(self):
        nodes = self.node.list_node_names_by_role("worker")
        for node_name in nodes:
            disks = self.node.list_disks_by_node_name(node_name)
            for disk_name in disks:
                self.node.set_disk_eviction_requested(node_name, disk_name, evictionRequested=False)
                self.node.set_disk_scheduling(node_name, disk_name, allowScheduling=True)

    def reset_node_scheduling(self):
        nodes = self.node.list_node_names_by_role("worker")
        for node_name in nodes:
            self.enable_node_scheduling(node_name)

    def reset_node_tags(self):
        nodes = self.node.list_node_names_by_role("worker")
        for node_name in nodes:
            logging(f"Resetting node {node_name} tags")
            self.set_node_tags(node_name)

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

    def remove_backing_image_files_on_node(self, bi_name, node_name):
        return self.node.remove_backing_image_files_on_node(bi_name, node_name)

    def set_backing_image_folder_immutable_on_node(self, bi_name, node_name):
        return self.node.set_backing_image_folder_immutable_on_node(bi_name, node_name)

    def set_backing_image_folder_mutable_on_node(self, bi_name, node_name):
        return self.node.set_backing_image_folder_mutable_on_node(bi_name, node_name)

    def wait_default_disk_file_system_changed(self, node_name):
        return self.node.wait_default_disk_file_system_changed(node_name)

    def wait_default_disk_unschedulable(self, node_name):
        return self.node.wait_default_disk_unschedulable(node_name)

    def delete_default_disk(self, node_name):
        self.node.delete_default_disk(node_name)

    def get_default_disk_uuid_on_node(self, node_name):
        return self.node.get_default_disk_uuid_on_node(node_name)

    def wait_for_longhorn_node_down(self, node_name):
        self.node.wait_for_longhorn_node_down(node_name)

    def wait_for_longhorn_node_up(self, node_name):
        self.node.wait_for_longhorn_node_up(node_name)

    def delete_disk(self, disk_name, node_name):
        return self.node.delete_disk(disk_name, node_name)

    def wait_disk_kept_unschedulable(self, disk_name, node_name, keep_rounds=DISK_UNSCHEDULABLE_KEEP_ROUNDS):
        return self.node.wait_disk_kept_unschedulable(disk_name, node_name, keep_rounds)
