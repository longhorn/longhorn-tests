import time

from instancemanager import V1_InstanceManager
from instancemanager import V2_InstanceManager

from utility.utility import logging
from utility.utility import get_retry_count_and_interval
from utility.utility import pod_exec
import utility.constant as constant

class instancemanager_keywords:

    def __init__(self):
        self.instancemanager = V1_InstanceManager()
        self.v2_instancemanager = V2_InstanceManager()
        self.retry_count, self.retry_interval = get_retry_count_and_interval()

    def wait_for_all_instance_manager_running(self):
        logging(f'Waiting for all instance manager running')
        self.instancemanager.wait_for_all_instance_manager_running()

    def wait_for_all_instance_manager_removed(self):
        logging(f'Waiting for all instance manager removed')
        self.instancemanager.wait_for_all_instance_manager_removed()

    def check_all_instance_managers_not_restart(self, data_engine="v1"):
        self.instancemanager.check_all_instance_managers_not_restart(data_engine)

    def wait_all_instance_managers_recreated(self, data_engine="v1"):
        self.instancemanager.wait_all_instance_managers_recreated(data_engine)

    def check_instance_manager_existence_on_node(self, node_name, engine_type, exist):
        logging(f"Checking {engine_type} instance manager exist = {exist} on node {node_name}")
        self.instancemanager.check_instance_manager_existence_on_node(node_name, engine_type, exist)

    def delete_instance_manager_on_node(self, node_name, engine_type):
        self.instancemanager.delete_instance_manager_on_node(node_name, engine_type)

    def wait_for_instance_manager_cr_engine_instances_to_be_cleaned_up(self, node_name, engine_type):
        self.instancemanager.wait_for_instance_manager_cr_engine_instances_to_be_cleaned_up(node_name, engine_type)

    def get_instance_manager_pod_on_node(self, node_name, engine_type):
        return self.instancemanager.get_instance_manager_pod_on_node(node_name, engine_type)

    def create_orphaned_replica(self, node_name, volume_name, engine_type):
        if engine_type == "v1":
            return self.instancemanager.create_orphaned_replica(node_name, volume_name)
        elif engine_type == "v2":
            return self.v2_instancemanager.create_orphaned_replica(node_name, volume_name)

    def wait_for_replica_deleted(self, node_name, replica_name, engine_type):
        if engine_type == "v1":
            self.instancemanager.wait_for_replica_deleted(node_name, replica_name)
        elif engine_type == "v2":
            self.v2_instancemanager.wait_for_replica_deleted(node_name, replica_name)

    def wait_for_replica_present(self, node_name, replica_name, engine_type):
        if engine_type == "v1":
            self.instancemanager.wait_for_replica_present(node_name, replica_name)
        elif engine_type == "v2":
            self.v2_instancemanager.wait_for_replica_present(node_name, replica_name)

    def verify_replica_lvol_exists_in_spdk_lvol(self, node_name, replica_name):
        logging(f"Verifying replica {replica_name} exists in SPDK on node {node_name}")
        self.instancemanager.verify_replica_lvol_exists_in_spdk_lvol(node_name, replica_name)

    def wait_for_disk_size_in_instance_manager_pod(self, instance_manager_name, device_name, expected_size):
        for i in range(self.retry_count):
            logging(f"Waiting for disk size in instance manager pod {instance_manager_name} to be {expected_size} ... ({i})")
            time.sleep(self.retry_interval)
            cmd = f"fdisk -l /dev/mapper/{device_name}"
            try:
                result = pod_exec(instance_manager_name, constant.LONGHORN_NAMESPACE, cmd)
                logging(f"Current disk info in instance manager pod {instance_manager_name}: {result}")
                if expected_size in result:
                    return
            except Exception as e:
                logging(f"Error checking disk size in instance manager pod {instance_manager_name}: {e}")
                continue

        assert False, f"Disk size in instance manager pod {instance_manager_name} does not contain {expected_size}"
