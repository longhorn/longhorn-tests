import json
import uuid
import time

from instancemanager.base import Base

from utility.utility import get_longhorn_client
from utility.utility import logging
from utility.utility import subprocess_exec_cmd
import utility.constant as constant
from utility.constant import DEFAULT_BLOCK_DISK_NAME

class V2_InstanceManager(Base):

    def __init__(self):
        super().__init__()

    def wait_for_all_instance_manager_running_with_default_image(self):
        longhorn_client = get_longhorn_client()
        worker_nodes = self.node.list_node_names_by_role("worker")
        default_instance_manager_image = longhorn_client.by_id_setting("default-instance-manager-image").value
        instance_managers = []
        instance_manager_map = {}

        for i in range(self.retry_count):
            try:
                instance_managers = longhorn_client.list_instance_manager()
                instance_manager_map = {}
                for im in instance_managers:
                    if im.currentState != "running":
                        continue
                    if im.image != default_instance_manager_image:
                        continue
                    instance_manager_map[im.nodeID] = im
                if len(instance_manager_map) == len(worker_nodes):
                    return
            except Exception as e:
                logging(f"Getting instance manager state/image error: {e}")

            logging(
                f"Waiting for all instance manager running with default image "
                f"{default_instance_manager_image}, retry ({i}) ..."
            )
            time.sleep(self.retry_interval)

        assert len(instance_manager_map) == len(worker_nodes), (
            f"expect all worker nodes to have running instance managers with "
            f"default image {default_instance_manager_image}, "
            f"instance_managers = {instance_managers}, "
            f"instance_manager_map = {instance_manager_map}"
        )

    def wait_for_all_instance_manager_upgrades_completed(self):
        for node_name in self.node.list_node_names_by_role("worker"):
            self.wait_for_instance_manager_upgrade_state_on_node(node_name, "completed")

    def wait_for_instance_manager_upgrade_to_start(self, node_name=None, timeout=None):
        retry_count = int(timeout) if timeout else self.retry_count
        cmd = (
            f"kubectl get instancemanagerupgrades.longhorn.io "
            f"-n {constant.LONGHORN_NAMESPACE} -ojson"
        )
        target = f"on node {node_name}" if node_name else "on any node"

        for i in range(retry_count):
            try:
                items = json.loads(subprocess_exec_cmd(cmd, verbose=False))["items"]
                if node_name:
                    items = [upgrade for upgrade in items if upgrade["spec"]["nodeID"] == node_name]
                if items:
                    logging(f"Instance manager upgrade started {target}: {items}")
                    return items
            except Exception as e:
                logging(f"Getting instance manager upgrades error: {e}")

            logging(f"Waiting for instance manager upgrade to start {target} ... ({i})")
            time.sleep(self.retry_interval)

        assert False, f"Failed to wait for instance manager upgrade to start {target}"

    def wait_for_instance_manager_upgrade_state_on_node(self, node_name, expected_state):
        cmd = (
            f"kubectl get instancemanagerupgrades.longhorn.io "
            f"-n {constant.LONGHORN_NAMESPACE} -ojson"
        )
        instance_manager_upgrade = None

        for i in range(self.retry_count):
            try:
                items = json.loads(subprocess_exec_cmd(cmd, verbose=False))["items"]
                instance_manager_upgrade = next(
                    (upgrade for upgrade in items if upgrade["spec"]["nodeID"] == node_name),
                    None,
                )
                if expected_state == "aborted":
                    reached = instance_manager_upgrade["status"]["abortRequested"]
                else:
                    reached = instance_manager_upgrade["status"]["state"] == expected_state
                if reached:
                    logging(f"Instance manager upgrade on node {node_name} is {expected_state}: {instance_manager_upgrade}")
                    return
            except Exception as e:
                logging(f"Getting instance manager upgrade on node {node_name} error: {e}")

            logging(f"Waiting for instance manager upgrade on node {node_name} to be {expected_state} ... ({i}): {instance_manager_upgrade}")
            time.sleep(self.retry_interval)

        assert False, (
            f"expect instance manager upgrade on node {node_name} to be {expected_state}, "
            f"but got {instance_manager_upgrade}"
        )

    def wait_for_instance_manager_image_on_node(self, node_name, expected_image):
        image = None

        for i in range(self.retry_count):
            try:
                image = self.get_instance_manager_image_on_node(node_name)
                if image == expected_image:
                    logging(f"Instance manager on node {node_name} is using image {expected_image}")
                    return
            except Exception as e:
                logging(f"Getting instance manager image on node {node_name} error: {e}")

            logging(f"Waiting for instance manager on node {node_name} to use image {expected_image}, current image {image} ... ({i})")
            time.sleep(self.retry_interval)

        assert False, f"Failed to wait for instance manager on node {node_name} to use image {expected_image}, current image {image}"

    def get_instance_manager_image_on_node(self, node_name):
        for im in get_longhorn_client().list_instance_manager():
            if im.nodeID == node_name and im.dataEngine == "v2":
                return im.image
        assert False, f"Failed to find v2 instance manager on node {node_name}"

    def get_replicas(self, node_name):
        im_pod_name = self.get_instance_manager_pod_on_node(node_name, "v2")
        cmd = f"kubectl exec -n {constant.LONGHORN_NAMESPACE} {im_pod_name} -- go-spdk-helper lvol get"
        output = subprocess_exec_cmd(cmd)
        return output

    def create_orphaned_replica(self, node_name, volume_name):
        orphaned_replica = f"{volume_name}-r-{uuid.uuid4().hex[:8]}"

        logging(f"Creating orphaned replica {orphaned_replica} on node {node_name} in lvs {DEFAULT_BLOCK_DISK_NAME}")

        im_pod_name = self.get_instance_manager_pod_on_node(node_name, "v2")
        cmd = (f"kubectl exec -n {constant.LONGHORN_NAMESPACE} {im_pod_name} -- "
               f"go-spdk-helper lvol create "
               f"--lvs-name {DEFAULT_BLOCK_DISK_NAME} "
               f"--lvol-name {orphaned_replica} "
               f"--size 1024")
        subprocess_exec_cmd(cmd)

        logging(f"Created orphaned replica {orphaned_replica} on node {node_name}")
        return orphaned_replica

    def permanently_crash_replica(self, node_name, replica_name):
        # `go-spdk-helper lvol delete` only temporarily crash a replica,
        # eventually the lvol will be recreated with the same replica name
        # (alias) but different uuid. From Longhorn's perspective the replica
        # looks like being reused.
        raise NotImplementedError(
            "permanently_crash_replica is not implemented for v2 volumes"
        )

    def wait_for_replica_deleted(self, node_name, replica_name):
        # v2 replica directory name is also not the same as v2 replica name
        # but since `go-spdk-helper lvol get` returns all detailed info including the replica name and replica directory name
        # it's safe to directly use the replica name for verification
        for i in range(self.retry_count):
            logging(f"Waiting for replica {replica_name} to be deleted from spdk on node {node_name} ... ({i})")
            try:
                replicas_output = self.get_replicas(node_name)
                if replica_name not in replicas_output:
                    return
            except Exception as e:
                logging(f"Failed to wait for replica {replica_name} to be deleted from spdk on node {node_name}: {e}")
            time.sleep(self.retry_interval)
        assert False, f"Failed to wait for replica {replica_name} to be deleted from spdk on node {node_name}"

    def wait_for_replica_present(self, node_name, replica_name):
        # v2 replica directory name is also not the same as v2 replica name
        # but since `go-spdk-helper lvol get` returns all detailed info including the replica name and replica directory name
        # it's safe to directly use the replica name for verification
        for i in range(self.retry_count):
            logging(f"Waiting for replica {replica_name} to be present in spdk on node {node_name} ... ({i})")
            try:
                replicas_output = self.get_replicas(node_name)
                if replica_name in replicas_output:
                    return
            except Exception as e:
                logging(f"Failed to wait for replica {replica_name} to be present in spdk on node {node_name}: {e}")
            time.sleep(self.retry_interval)
        assert False, f"Failed to wait for replica {replica_name} to be present in spdk on node {node_name}"
