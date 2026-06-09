from instancemanager import InstanceManager

from utility.utility import logging


class instancemanager_keywords:

    def __init__(self):
        self.instancemanager = InstanceManager()

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

    def kill_engine_process(self, instance_manager_name, volume_name):
        self.instancemanager.kill_engine_process(instance_manager_name, volume_name)

    def get_instance_manager_pod_on_node(self, node_name, engine_type):
        return self.instancemanager.get_instance_manager_pod_on_node(node_name, engine_type)

    def verify_replica_lvol_deleted_from_spdk_lvol(self, node_name, replica_name):
        logging(f"Verifying replica {replica_name} is deleted from SPDK on node {node_name}")
        self.instancemanager.verify_replica_lvol_deleted_from_spdk_lvol(node_name, replica_name)

    def verify_replica_lvol_exists_in_spdk_lvol(self, node_name, replica_name):
        logging(f"Verifying replica {replica_name} exists in SPDK on node {node_name}")
        self.instancemanager.verify_replica_lvol_exists_in_spdk_lvol(node_name, replica_name)
