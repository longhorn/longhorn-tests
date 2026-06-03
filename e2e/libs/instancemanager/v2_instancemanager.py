import uuid
import time

from instancemanager.base import Base

from utility.utility import logging
from utility.utility import subprocess_exec_cmd
import utility.constant as constant
from utility.constant import DEFAULT_BLOCK_DISK_NAME

import json

class V2_InstanceManager(Base):

    def __init__(self):
        super().__init__()

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

    def get_spdk_raid_bdevs(self, node_name):
        logging(f"Getting SPDK raid bdevs on node {node_name}")
        im_pod_name = self.get_instance_manager_pod_on_node(node_name, "v2")
        cmd = f"kubectl exec -n {constant.LONGHORN_NAMESPACE} {im_pod_name} -- go-spdk-helper raid get"
        output = subprocess_exec_cmd(cmd)
        logging(f"SPDK raid bdevs output on node {node_name}:\n{output}")
        return output

    def verify_raid_bdev_exists_on_node(self, node_name):
        logging(f"Verifying raid bdev exists on node {node_name}")
        for i in range(self.retry_count):
            try:
                raid_output = self.get_spdk_raid_bdevs(node_name)
                # Parse JSON output
                raid_bdevs = json.loads(raid_output)
                # Check if array is not empty (raid bdevs exist)
                if isinstance(raid_bdevs, list) and len(raid_bdevs) > 0:
                    logging(f"Verified raid bdev exists on node {node_name}: found {len(raid_bdevs)} raid bdev(s)")
                    return
                logging(f"No raid bdev found on node {node_name} (empty array), retrying ... ({i})")
                time.sleep(self.retry_interval)
            except json.JSONDecodeError as e:
                logging(f"Error parsing SPDK raid bdevs JSON on node {node_name}: {e}")
                time.sleep(self.retry_interval)
            except Exception as e:
                logging(f"Error checking SPDK raid bdevs: {e}")
                time.sleep(self.retry_interval)
        assert False, f"No raid bdev found on node {node_name} after {self.retry_count} retries"

    def verify_raid_bdev_not_exists_on_node(self, node_name):
        logging(f"Verifying raid bdev does not exist on node {node_name}")
        for i in range(self.retry_count):
            try:
                raid_output = self.get_spdk_raid_bdevs(node_name)
                # Parse JSON output
                raid_bdevs = json.loads(raid_output)
                # Check if array is empty (no raid bdevs)
                if isinstance(raid_bdevs, list) and len(raid_bdevs) == 0:
                    logging(f"Verified no raid bdev on node {node_name} (empty array)")
                    return
                logging(f"Raid bdev still exists on node {node_name}: found {len(raid_bdevs)} raid bdev(s), retrying ... ({i})")
                time.sleep(self.retry_interval)
            except json.JSONDecodeError as e:
                logging(f"Error parsing SPDK raid bdevs JSON on node {node_name}: {e}")
                time.sleep(self.retry_interval)
            except Exception as e:
                logging(f"Error checking SPDK raid bdevs: {e}")
                time.sleep(self.retry_interval)
        assert False, f"Raid bdev still exists on node {node_name} after {self.retry_count} retries"

    def verify_replica_lvol_exists_in_spdk_lvol(self, node_name, replica_name):
        logging(f"Verifying replica {replica_name} exists in SPDK on node {node_name}")
        for i in range(self.retry_count):
            try:
                lvols_output = self.get_spdk_lvols(node_name)
                if replica_name in lvols_output:
                    logging(f"Verified replica {replica_name} exists in SPDK on node {node_name}")
                    return
                logging(f"Replica {replica_name} not found in SPDK on node {node_name}, retrying ... ({i})")
                time.sleep(self.retry_interval)
            except Exception as e:
                logging(f"Error checking SPDK lvols: {e}")
                time.sleep(self.retry_interval)
        assert False, f"Replica {replica_name} not found in SPDK on node {node_name} after {self.retry_count} retries"
