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

    @classmethod
    def restart_kubelet(cls, node_name, interval_time):
        logging.info(f"restarting kubelet on node instances: {node_name}")
        node_instances = cls._instance.get_node_instance(node_name)

        k8s_distro = globalVars.variables["K8S_DISTRO"]
        if k8s_distro == 'rke2':
            cmd_stop = 'sudo systemctl stop rke2-server.service'
            cmd_start = 'sudo systemctl start rke2-server.service'
            cmd_restart = 'sudo systemctl restart rke2-server.service'
        elif k8s_distro == 'rke1':
            cmd_stop = 'sudo docker stop kubelet'
            cmd_start = 'sudo docker run kubelet'
            cmd_restart = 'sudo docker restart kubelet'
        elif k8s_distro == 'k3s':
            cmd_stop = 'systemctl stop k3s-agent.service'
            cmd_start = 'systemctl start k3s-agent.service'
            cmd_restart = 'systemctl restart k3s-agent.service'
        else:
            raise Exception(f'Unsupported K8S distros: {k8s_distro}')

        for instance in node_instances:
            ip_address = instance.public_ip_address
            if int(interval_time) == 0:
                Utility.ssh_and_exec_cmd(ip_address, cmd_restart)
            else:
                # stop all nodes kubelet service
                Utility.ssh_and_exec_cmd(ip_address, cmd_stop)
                # wait for some time
                time.sleep(int(interval_time))
                # start all nodes kubelet service
                Utility.ssh_and_exec_cmd(ip_address, cmd_start)
