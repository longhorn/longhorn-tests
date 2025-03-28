import time
import re
import os

from kubernetes import client
from robot.libraries.BuiltIn import BuiltIn

from utility.constant import DISK_BEING_SYNCING
from utility.constant import LONGHORN_NAMESPACE
from utility.constant import NODE_UPDATE_RETRY_INTERVAL
from utility.utility import get_longhorn_client
from utility.utility import get_retry_count_and_interval
from utility.utility import logging
from node_exec import NodeExec

class Node:

    DEFAULT_DISK_PATH = "/var/lib/longhorn/"
    DEFAULT_VOLUME_PATH = "/dev/longhorn/"

    def __init__(self):
        self.retry_count, self.retry_interval = get_retry_count_and_interval()

    def mount_disk(self, disk_name, node_name):
        mount_path = os.path.join(self.DEFAULT_DISK_PATH, disk_name)
        device_path = os.path.join(self.DEFAULT_VOLUME_PATH, disk_name)
        cmd = f"mkdir -p {mount_path}"
        res = NodeExec(node_name).issue_cmd(cmd)
        cmd = f"mkfs.ext4 {device_path}"
        res = NodeExec(node_name).issue_cmd(cmd)
        cmd = f"mount {device_path} {mount_path}"
        res = NodeExec(node_name).issue_cmd(cmd)
        return mount_path

    def update_disks(self, node_name, disks):
        node = get_longhorn_client().by_id_node(node_name)
        logging(f"Updating node {node_name} disks {disks}")
        for _ in range(self.retry_count):
            try:
                node.diskUpdate(disks=disks)
                self.wait_for_disk_update(node_name, len(disks))
                return
            except Exception as e:
                logging(f"Failed to update node {node_name} disk: {e}")
            time.sleep(self.retry_interval)
        assert False, f"Failed to update node {node_name} disk {disks}"

    def wait_for_disk_update(self, node_name, disk_num):
        for i in range(self.retry_count):
            node = get_longhorn_client().by_id_node(node_name)
            if len(node.disks) == disk_num:
                all_updated = True
                disks = node.disks
                for d in disks:
                    if disks[d]["diskUUID"] == "" or \
                        (disks[d]["allowScheduling"] and
                        (not disks[d]["conditions"] or
                        disks[d]["conditions"]["Ready"]["status"] != "True")):
                        logging(f"Waiting for node {node_name} disk {d} updated ... ({i})")
                        all_updated = False
                        break
                if all_updated:
                    break
            time.sleep(self.retry_interval)
        assert len(node.disks) == disk_num and all_updated, f"Waiting for node {node_name} disk updated to {disk_num} failed: {disks}"

    def add_disk(self, node_name, disk):
        added = False
        for i in range(self.retry_count):
            logging(f"Adding disk {disk} to node {node_name} ... ({i})")
            try:
                node = get_longhorn_client().by_id_node(node_name)
                disks = node.disks
                disks.update(disk)
                self.update_disks(node_name, disks)
                added = True
                break
            except Exception as e:
                logging(f"Adding disk {disk} to node {node_name} error: {e}")
            time.sleep(self.retry_interval)
        assert added, f"Adding disk {disk} to node {node_name} failed"

    def reset_disks(self, node_name):
        node = get_longhorn_client().by_id_node(node_name)

        for disk_name, disk in iter(node.disks.items()):
            if disk.path != self.DEFAULT_DISK_PATH:
                disk.allowScheduling = False
                logging(f"Disabling scheduling disk {disk_name} on node {node_name}")
            else:
                disk.allowScheduling = True
                logging(f"Enabling scheduling disk {disk_name} on node {node_name}")
        self.update_disks(node_name, node.disks)

        disks = {}
        for disk_name, disk in iter(node.disks.items()):
            if disk.path == self.DEFAULT_DISK_PATH:
                disks[disk_name] = disk
                disk.allowScheduling = True
                logging(f"Keeping disk {disk_name} on node {node_name}")
            else:
                logging(f"Removing disk {disk_name} from node {node_name}")
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

    def get_node_by_name(self, node_name, namespace="kube-system"):
        logging(f"Getting node by name {node_name} in namespace {namespace}")
        try:
            if namespace == LONGHORN_NAMESPACE:
                return get_longhorn_client().by_id_node(node_name)
            else:
                core_api = client.CoreV1Api()
                return core_api.read_node(node_name)
        except Exception as e:
            logging(f"Getting node by name {node_name} in namespace {namespace} failed: {e}")
            return None

    def get_node_cpu_cores(self, node_name):
        node = self.get_node_by_name(node_name)
        return node.status.capacity['cpu']

    def get_node_total_memory(self, node_name):
        node = self.get_node_by_name(node_name)
        return node.status.capacity['memory']

    def get_node_condition(self, node_name, condition_type):
        node = self.get_node_by_name(node_name)
        for condition in node.status.conditions:
            if condition.type == condition_type:
                logging(f"Got node {node_name} condition {condition_type}: {condition}")
                return condition.status
        assert False, f"Failed to get node {node_name} condition {condition_type}: {node}"

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

        all_nodes = sorted(filter_nodes(nodes, lambda node: True))

        control_plane_labels = {
            "node-role.kubernetes.io/master": "true",
            "node-role.kubernetes.io/control-plane": "true",
            "node-role.kubernetes.io/control-plane": "",
            "talos.dev/owned-labels": "[\"node-role.kubernetes.io/control-plane\"]"
        }
        condition = lambda node: any(label in node.metadata.labels.keys() and node.metadata.labels[label] == value for label, value in control_plane_labels.items())
        control_plane_nodes = sorted(filter_nodes(nodes, condition))

        worker_nodes = sorted([node for node in all_nodes if node not in control_plane_nodes])

        if role == "all":
            return all_nodes
        elif role == "control-plane":
            return control_plane_nodes
        elif role == "worker":
            return worker_nodes

    def set_node(self, node_name: str, allowScheduling: bool, evictionRequested: bool) -> object:
        for _ in range(self.retry_count):
            try:
                node = get_longhorn_client().by_id_node(node_name)

                get_longhorn_client().update(
                    node,
                    allowScheduling=allowScheduling,
                    evictionRequested=evictionRequested
                )

                node = get_longhorn_client().by_id_node(node_name)
                assert node.allowScheduling == allowScheduling
                assert node.evictionRequested == evictionRequested
                return node
            except Exception as e:
                logging(f"Updating node {node_name} error: {e}")

            time.sleep(self.retry_interval)

        raise AssertionError(f"Updating node {node_name} failed")

    def set_node_scheduling(self, node_name, allowScheduling=True, retry=True):
        node = get_longhorn_client().by_id_node(node_name)

        if node.tags is None:
           node.tags = []

        if not retry:
            get_longhorn_client().update(node, allowScheduling=allowScheduling)

        # Retry if "too many retries error" happened.
        for i in range(self.retry_count):
            logging(f"Setting node {node_name} allowScheduling to {allowScheduling} ... ({i})")
            try:
                node = get_longhorn_client().update(node, allowScheduling=allowScheduling,
                                 tags=node.tags)
            except Exception as e:
                logging(f"Setting node {node_name} allowScheduling to {allowScheduling} failed: {e}")
                if DISK_BEING_SYNCING in str(e.error.message):
                    time.sleep(NODE_UPDATE_RETRY_INTERVAL)
                    continue
                raise
            else:
                break

        return node

    def set_default_disk_scheduling(self, node_name, allowScheduling):
        node = get_longhorn_client().by_id_node(node_name)

        for disk_name, disk in iter(node.disks.items()):
            if disk.path == self.DEFAULT_DISK_PATH:
                disk.allowScheduling = allowScheduling
        self.update_disks(node_name, node.disks)

    def set_disk_scheduling(self, node_name, disk_name, allowScheduling):
        logging(f"Setting node {node_name} disk {disk_name} allowScheduling to {allowScheduling}")
        node = get_longhorn_client().by_id_node(node_name)

        for name, disk in iter(node.disks.items()):
            if name == disk_name:
                disk.allowScheduling = allowScheduling
        self.update_disks(node_name, node.disks)

    def check_node_schedulable(self, node_name, schedulable):
        node = get_longhorn_client().by_id_node(node_name)
        for _ in range(self.retry_count):
            if node["conditions"]["Schedulable"]["status"] == schedulable:
                break
            time.sleep(self.retry_interval)
        assert node["conditions"]["Schedulable"]["status"] == schedulable

    def is_node_schedulable(self, node_name):
        node = get_longhorn_client().by_id_node(node_name)
        return node["conditions"]["Schedulable"]["status"]

    def is_disk_in_pressure(self, node_name, disk_name):
        node = get_longhorn_client().by_id_node(node_name)
        return node["disks"][disk_name]["conditions"]["Schedulable"]["reason"] == "DiskPressure"

    def wait_for_disk_in_pressure(self, node_name, disk_name):
        for i in range(self.retry_count):
            is_in_pressure = self.is_disk_in_pressure(node_name, disk_name)
            logging(f"Waiting for disk {disk_name} on node {node_name} in pressure ... ({i})")
            if is_in_pressure:
                break
            time.sleep(self.retry_interval)
        assert self.is_disk_in_pressure(node_name, disk_name), f"Waiting for node {node_name} disk {disk_name} in pressure failed: {get_longhorn_client().by_id_node(node_name)}"

    def wait_for_disk_not_in_pressure(self, node_name, disk_name):
        for i in range(self.retry_count):
            is_in_pressure = self.is_disk_in_pressure(node_name, disk_name)
            logging(f"Waiting for disk {disk_name} on node {node_name} not in pressure ... ({i})")
            if not is_in_pressure:
                break
            time.sleep(self.retry_interval)
        assert not self.is_disk_in_pressure(node_name, disk_name), f"Waiting for node {node_name} disk {disk_name} not in pressure failed: {get_longhorn_client().by_id_node(node_name)}"

    def get_disk_uuid(self, node_name, disk_name):
        node = get_longhorn_client().by_id_node(node_name)
        uuid = node["disks"][disk_name]["diskUUID"]
        logging(f"Got node {node_name} disk {disk_name} uuid = {uuid}")
        return uuid

    def wait_for_node_down(self, node_name):
        for i in range(self.retry_count):
            logging(f"Waiting for k8s node {node_name} down ... ({i})")
            node = self.get_node_by_name(node_name)
            if not node:
                return
            else:
                for condition in node.status.conditions:
                    if condition.type == "Ready" and condition.status != "True":
                        return
            time.sleep(self.retry_interval)
        assert False, f"Waiting for node {node_name} down failed: {node}"

    def wait_for_node_up(self, node_name):
        up = False
        for i in range(self.retry_count):
            logging(f"Waiting for k8s node {node_name} up ... ({i})")
            node = self.get_node_by_name(node_name)
            if node:
                for condition in node.status.conditions:
                    if condition.type == "Ready" and condition.status == "True":
                        return
            time.sleep(self.retry_interval)
        assert False, f"Waiting for node {node_name} up failed: {node}"

    def list_dm_devices(self, node_name):
        cmd = "dmsetup ls | awk '{print $1}'"
        res = NodeExec(node_name).issue_cmd(cmd)
        return res

    def list_volume_devices(self, node_name):
        cmd = "ls /dev/longhorn/"
        res = NodeExec(node_name).issue_cmd(cmd)
        return res
