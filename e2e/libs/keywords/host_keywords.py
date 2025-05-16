from robot.libraries.BuiltIn import BuiltIn

import os

from host import Harvester, Aws, Vagrant
from host.constant import NODE_REBOOT_DOWN_TIME_SECOND

from node import Node

from utility.utility import logging


class host_keywords:
    _host_providers = {
        "aws": Aws,
        "harvester": Harvester,
        "vagrant": Vagrant,
    }

    def __init__(self):
        self.volume_keywords = BuiltIn().get_library_instance('volume_keywords')
        self.host = self._create_host(os.getenv('HOST_PROVIDER', 'vagrant'))
        self.node = Node()

    @classmethod
    def _create_host(cls, host_provider):
        host_constructor = cls._host_providers.get(host_provider)
        if host_constructor is None:
            raise Exception(f"Unsupported host provider {host_provider}")
        return host_constructor()

    def reboot_node_by_index(self, idx, power_off_time_in_min=1):
        node_name = self.node.get_node_by_index(idx)
        reboot_down_time_sec = int(power_off_time_in_min) * 60

        logging(f'Rebooting node {node_name} with downtime {reboot_down_time_sec} seconds')
        self.host.reboot_node(node_name, reboot_down_time_sec)

    def reboot_all_worker_nodes(self, power_off_time_in_min=1):
        reboot_down_time_sec = int(power_off_time_in_min) * 60

        logging(f'Rebooting all worker nodes with downtime {reboot_down_time_sec} seconds')
        self.host.reboot_all_worker_nodes(reboot_down_time_sec)

    def reboot_all_nodes(self):
        logging(f'Rebooting all nodes with downtime {NODE_REBOOT_DOWN_TIME_SECOND} seconds')
        self.host.reboot_all_nodes()

    def reboot_node_by_name(self, node_name, downtime_in_min=1):
        reboot_down_time_sec = int(downtime_in_min) * 60

        logging(f'Rebooting node {node_name} with downtime {reboot_down_time_sec} seconds')
        self.host.reboot_node(node_name, reboot_down_time_sec)

    def power_off_volume_node(self, volume_name, waiting=True):
        node_id = self.volume_keywords.get_node_id_by_replica_locality(volume_name, "volume node")
        logging(f'Power off volume {volume_name} node {node_id} with waiting = {waiting}')
        self.host.power_off_node(node_id, waiting)

    def power_on_node_by_name(self, node_name):
        self.host.power_on_node(node_name)

    def power_off_node_by_name(self, node_name, waiting=True):
        self.host.power_off_node(node_name, waiting)
