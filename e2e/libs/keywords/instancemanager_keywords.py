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
