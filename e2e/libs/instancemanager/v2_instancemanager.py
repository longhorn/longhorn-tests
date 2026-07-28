import uuid
import time

from instancemanager.base import Base

from utility.utility import logging
from utility.utility import subprocess_exec_cmd
import utility.constant as constant
from utility.constant import DEFAULT_BLOCK_DISK_NAME

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
