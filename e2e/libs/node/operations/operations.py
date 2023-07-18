import time
import logging
import subprocess

from functools import partial
from multiprocessing import Pool
from strategy import CloudProvider
from node.operations.aws import EC2
from node.operations.local_cluster import LocalCluster
from utility import globalVars, Utility
from volume.rest_volume import RestVolume

class Operations:

    _instance = None

    def __init__(self, cloud_provider):
        if cloud_provider == CloudProvider.AWS.value:
            logging.info("cloude provider: AWS")
            self.__class__._instance  = EC2()
        elif cloud_provider == CloudProvider.LOCAL_CLUSTER.value:
            logging.info("cloude provider: Local")
            self.__class__._instance = LocalCluster()
        else:
            Exception(f"could not recognize the cloud provider: {cloud_provider}")

    @classmethod
    def cleanup(cls):
        # Turn the power off node back
        cls._instance.power_on_node_instance()

    @classmethod
    def power_off_node(cls, node_name):
        cls._instance.power_off_node_instance(node_name)

    @classmethod
    def power_on_node(cls, node_name):
        cls._instance.power_on_node_instance(node_name)

    @classmethod
    def reboot_node(cls, node_name):
        cls._instance.reboot_node_instance(node_name)
