import os
import time
import re
from kubernetes import client

from robot.libraries.BuiltIn import BuiltIn
from utility.utility import get_longhorn_client
from utility.utility import get_retry_count_and_interval
from utility.utility import logging


class Node:

    DEFAULT_DISK_PATH = "/var/lib/longhorn/"

    def __init__(self):
        self.longhorn_client = get_longhorn_client()
        self.retry_count, self.retry_interval = get_retry_count_and_interval()

    def update_disks(self, node_name, disks):
        node = self.longhorn_client.by_id_node(node_name)
        for _ in range(self.retry_count):
            try:
                node.diskUpdate(disks=disks)
                break
            except Exception as e:
                logging(f"Updating node {node_name} disk error: {e}")
            time.sleep(self.retry_interval)

    def add_disk(self, node_name, disk):
        node = self.longhorn_client.by_id_node(node_name)
        disks = node.disks
        disks.update(disk)
        self.update_disks(node_name, disks)

    def reset_disks(self, node_name):
        node = self.longhorn_client.by_id_node(node_name)

        for disk_name, disk in iter(node.disks.items()):
            if disk.path != self.DEFAULT_DISK_PATH:
                disk.allowScheduling = False
        self.update_disks(node_name, node.disks)

        disks = {}
        for disk_name, disk in iter(node.disks.items()):
            if disk.path == self.DEFAULT_DISK_PATH:
                disks[disk_name] = disk
            else:
                logging(f"Try to remove disk {disk_name} from node {node_name}")
        self.update_disks(node_name, disks)

    def is_accessing_node_by_index(self, node):
        p = re.compile('node (\d)')
        if m := p.match(node):
            return m.group(1)
        else:
            return None

    def get_node_by_index(self, index, role="worker"):
        nodes = self.list_node_names_by_role(role)
        return nodes[int(index)]

    def get_node_by_name(self, node_name):
        core_api = client.CoreV1Api()
        return core_api.read_node(node_name)

    def get_node_cpu_cores(self, node_name):
        node = self.get_node_by_name(node_name)
        return node.status.capacity['cpu']

    def list_node_names_by_volumes(self, volume_names):
        volume_keywords = BuiltIn().get_library_instance('volume_keywords')
        volume_nodes = {}
        for volume_name in volume_names:
            volume_node = volume_keywords.get_node_id_by_replica_locality(volume_name, "volume node")
            if volume_node not in volume_nodes:
                volume_nodes[volume_node] = True
        return list(volume_nodes.keys())

    def list_node_names_by_role(self, role="all"):
        if role not in ["all", "control-plane", "worker"]:
            raise ValueError("Role must be one of 'all', 'master' or 'worker'")

        def filter_nodes(nodes, condition):
            return [node.metadata.name for node in nodes if condition(node)]

        core_api = client.CoreV1Api()
        nodes = core_api.list_node().items

        control_plane_labels = ['node-role.kubernetes.io/master', 'node-role.kubernetes.io/control-plane']

        if role == "all":
            return sorted(filter_nodes(nodes, lambda node: True))

        if role == "control-plane":
            condition = lambda node: all(label in node.metadata.labels for label in control_plane_labels)
            return sorted(filter_nodes(nodes, condition))

        if role == "worker":
            condition = lambda node: not any(label in node.metadata.labels for label in control_plane_labels)
            return sorted(filter_nodes(nodes, condition))
