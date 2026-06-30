import re
import uuid
import time

from instancemanager.base import Base

from utility.utility import logging
from utility.utility import subprocess_exec_cmd
import utility.constant as constant

class V1_InstanceManager(Base):

    def __init__(self):
        super().__init__()

    def get_replicas(self, node_name):
        im_pod_name = self.get_instance_manager_pod_on_node(node_name, "v1")
        cmd = f"kubectl exec -n {constant.LONGHORN_NAMESPACE} {im_pod_name} -- ls /host/var/lib/longhorn/replicas"
        output = subprocess_exec_cmd(cmd)
        return output

    def create_orphaned_replica(self, node_name, volume_name):
        replicas_output = self.get_replicas(node_name)

        # Match the replica directory named {volume_name}-{8-hex-chars}
        pattern = re.compile(
            rf'^({re.escape(volume_name)}-[0-9a-f]{{8}})$',
            re.MULTILINE
        )
        match = pattern.search(replicas_output)

        src_replica = match.group(1)
        orphaned_replica = f"{volume_name}-{uuid.uuid4().hex[:8]}"

        logging(f"Creating orphaned replica {orphaned_replica} from {src_replica} on node {node_name}")

        im_pod_name = self.get_instance_manager_pod_on_node(node_name, "v1")
        replicas_dir = "/host/var/lib/longhorn/replicas"
        cmd = (f"kubectl exec -n {constant.LONGHORN_NAMESPACE} {im_pod_name} -- "
               f"cp -r {replicas_dir}/{src_replica} {replicas_dir}/{orphaned_replica}")
        subprocess_exec_cmd(cmd)

        logging(f"Created orphaned replica {orphaned_replica} on node {node_name}")
        return orphaned_replica

    def get_replica_directory_name(self, replica_name):
        cmd = (f"kubectl get replicas -n {constant.LONGHORN_NAMESPACE} {replica_name} "
               f"-ojsonpath='{{.spec.dataDirectoryName}}'")
        return subprocess_exec_cmd(cmd)

    def wait_for_replica_deleted(self, node_name, replica_name):
        try:
            # if it's a real volume replica, since replica directory name is not the same as replica name,
            # we need to get the replica directory name from the replica name first
            replica_dir = self.get_replica_directory_name(replica_name)
        except Exception as e:
            # if it's a fake replica created manually, we can directly use it
            # since it was created it copying the replica directory name
            replica_dir = replica_name
        for i in range(self.retry_count):
            logging(f"Waiting for replica directory {replica_dir} for replica {replica_name} to be deleted from host /var/lib/longhorn/replicas on node {node_name} ... ({i})")
            try:
                replicas_output = self.get_replicas(node_name)
                if replica_dir not in replicas_output:
                    return
            except Exception as e:
                logging(f"Failed to wait for replica directory {replica_dir} for replica {replica_name} to be deleted from host /var/lib/longhorn/replicas on node {node_name}: {e}")
            time.sleep(self.retry_interval)
        assert False, f"Failed to wait for replica directory {replica_dir} for replica {replica_name} to be deleted from host /var/lib/longhorn/replicas on node {node_name}"

    def wait_for_replica_present(self, node_name, replica_name):
        try:
            # if it's a real volume replica, since replica directory name is not the same as replica name,
            # we need to get the replica directory name from the replica name first
            replica_dir = self.get_replica_directory_name(replica_name)
        except Exception as e:
            # if it's a fake replica created manually, we can directly use it
            # since it was created it copying the replica directory name
            replica_dir = replica_name
        for i in range(self.retry_count):
            logging(f"Waiting for replica directory {replica_dir} for replica {replica_name} to be present in host /var/lib/longhorn/replicas on node {node_name} ... ({i})")
            try:
                replicas_output = self.get_replicas(node_name)
                if replica_dir in replicas_output:
                    return
            except Exception as e:
                logging(f"Failed to wait for replica directory {replica_dir} for replica {replica_name} to be present in host /var/lib/longhorn/replicas on node {node_name}: {e}")
            time.sleep(self.retry_interval)
        assert False, f"Failed to wait for replica directory {replica_dir} for replica {replica_name} to be present in host /var/lib/longhorn/replicas on node {node_name}"
