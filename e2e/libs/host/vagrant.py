import csv
import os
import subprocess
import sys
import time

from host.constant import NODE_REBOOT_DOWN_TIME_SECOND
from host.base import Base

from utility.utility import logging
from utility.utility import wait_for_cluster_ready


class Vagrant(Base):
    _CMD_UP = 'up'
    _CMD_RELOAD = 'reload'
    _CMD_HALT = 'halt'
    _CMD_STATUS = 'status'

    def __init__(self):
        """
        Note: all the environment variables will pass to the Vagrant subprocesses.
        https://developer.hashicorp.com/vagrant/docs/other/environmental-variables
        """
        cmd_bin = os.getenv('VAGRANT_CMD') or 'vagrant'
        node_mapping = self._get_node_mapping(cmd_bin)
        logging(f'vagrant nodes: {node_mapping}')

        super().__init__(mapping=node_mapping)
        self._bin = cmd_bin

    @classmethod
    def _get_node_mapping(cls, cmd_bin):
        encoding = 'ascii'
        output = subprocess.check_output([cmd_bin, cls._CMD_STATUS, '--machine-readable']).decode(encoding)
        nodes = set(row[1] for row in csv.reader(output.splitlines()) if row[1])
        return {node: node for node in nodes}

    def reboot_all_nodes(self, shut_down_time_in_sec=NODE_REBOOT_DOWN_TIME_SECOND):
        self._vagrant_cmd(self._CMD_RELOAD)

        logging(f'Wait for {shut_down_time_in_sec} seconds before starting all vms')
        time.sleep(shut_down_time_in_sec)
        wait_for_cluster_ready()
        logging(f'Started all instances')

    def reboot_node(self, reboot_node_name, shut_down_time_in_sec=NODE_REBOOT_DOWN_TIME_SECOND):
        self._vagrant_cmd(self._CMD_RELOAD, reboot_node_name)
        logging(f'Wait for {shut_down_time_in_sec} seconds before starting vm {reboot_node_name}')
        time.sleep(shut_down_time_in_sec)
        logging(f'Started instances {reboot_node_name}')

    def reboot_all_worker_nodes(self, shut_down_time_in_sec=NODE_REBOOT_DOWN_TIME_SECOND):
        instance_list = self.node.list_node_names_by_role('worker')
        self._vagrant_cmd(self._CMD_RELOAD, *instance_list)
        logging(f'Wait for {shut_down_time_in_sec} seconds before starting worker vms')
        time.sleep(shut_down_time_in_sec)
        logging(f'Started worker instances')

    def power_off_node(self, power_off_node_name, waiting=True):
        self._vagrant_cmd(self._CMD_HALT, power_off_node_name)
        logging(f'Stopping instance {power_off_node_name}')
        if waiting:
            logging(f'Stopped instance {power_off_node_name}')
            self.node.wait_for_node_down(power_off_node_name)

    def power_on_node(self, power_on_node_name):
        self._vagrant_cmd(self._CMD_UP, power_on_node_name)
        logging(f'Started instance {power_on_node_name}')
        self.node.wait_for_node_up(power_on_node_name)

    def _vagrant_cmd(self, *args, **kwargs):
        return subprocess.check_call([self._bin]+list(args), stdout=sys.stdout, stderr=sys.stderr, **kwargs)
