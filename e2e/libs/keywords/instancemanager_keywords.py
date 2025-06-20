from instancemanager import InstanceManager

from utility.utility import logging


class instancemanager_keywords:

    def __init__(self):
        self.instancemanager = InstanceManager()

    def wait_for_all_instance_manager_running(self):
        logging(f'Waiting for all instance manager running')
        self.instancemanager.wait_for_all_instance_manager_running()

    def check_all_instance_managers_not_restart(self):
        self.instancemanager.check_all_instance_managers_not_restart()

    def wait_all_instance_managers_recreated(self):
        self.instancemanager.wait_all_instance_managers_recreated()

    def check_instance_manager_existence_on_node(self, node_name, engine_type, exist):
        logging(f"Checking {engine_type} instance manager exist = {exist} on node {node_name}")
        self.instancemanager.check_instance_manager_existence_on_node(node_name, engine_type, exist)

    def delete_instance_manager_on_node(self, node_name, engine_type):
        self.instancemanager.delete_instance_manager_on_node(node_name, engine_type)
