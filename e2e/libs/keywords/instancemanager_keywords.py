from instancemanager import V1_InstanceManager
from instancemanager import V2_InstanceManager

from utility.utility import logging

class instancemanager_keywords:

    def __init__(self):
        self.instancemanager = V1_InstanceManager()
        self.v2_instancemanager = V2_InstanceManager()

    def wait_for_all_instance_manager_running(self):
        logging(f'Waiting for all instance manager running')
        self.instancemanager.wait_for_all_instance_manager_running()

    def wait_for_all_instance_manager_removed(self):
        logging(f'Waiting for all instance manager removed')
        self.instancemanager.wait_for_all_instance_manager_removed()

    def check_all_instance_managers_not_restart(self):
        self.instancemanager.check_all_instance_managers_not_restart()

    def wait_all_instance_managers_recreated(self):
        self.instancemanager.wait_all_instance_managers_recreated()

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
        self.v2_instancemanager.verify_replica_lvol_exists_in_spdk_lvol(node_name, replica_name)

    def verify_raid_bdev_exists_on_node(self, node_name):
        logging(f"Verifying raid bdev exists on node {node_name}")
        self.v2_instancemanager.verify_raid_bdev_exists_on_node(node_name)

    def verify_raid_bdev_not_exists_on_node(self, node_name):
        logging(f"Verifying raid bdev does not exist on node {node_name}")
        self.v2_instancemanager.verify_raid_bdev_not_exists_on_node(node_name)

    def record_instance_manager_pod_uids(self, engine_type="v1"):
        logging(f"Recording {engine_type} instance manager pod UIDs")
        return self.instancemanager.record_instance_manager_pod_uids(engine_type)

    def check_instance_managers_not_restarted(self, engine_type="v1", recorded_pod_uids=None):
        logging(f"Checking {engine_type} instance managers did not restart")
        self.instancemanager.check_instance_managers_not_restarted(engine_type, recorded_pod_uids)
