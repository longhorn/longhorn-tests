from robot.libraries.BuiltIn import BuiltIn

import os
import threading
import time

from host import Harvester, Aws, Vagrant
from host.constant import NODE_REBOOT_DOWN_TIME_SECOND

from node import Node
from node_exec import NodeExec
from ssh.ssh import ssh_exec

from utility.utility import logging


class host_keywords:
    _host_providers = {
        "aws": Aws,
        "harvester": Harvester,
        "vagrant": Vagrant,
    }

    # Class-level monitor thread shared across all instances
    _monitor_thread = None

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

    def create_vm_snapshot(self, node_name):
        self.host.create_snapshot(node_name)

    def cleanup_vm_snapshots(self):
        self.host.cleanup_snapshots()

    def execute_command_on_node(self, cmd, node_name):
        return NodeExec(node_name).issue_cmd(cmd)

    def execute_command_on_node_and_not_expect_output(self, cmd, node_name, output):
        from utility.utility import get_retry_count_and_interval
        import time
        
        retry_count, _ = get_retry_count_and_interval()
        res = NodeExec(node_name).issue_cmd(cmd)
        if output in res:
            logging(f"Unexpected {output} in {cmd} result on node {node_name}: {res}")
            time.sleep(retry_count)  # Long sleep for debugging
            assert False, f"Unexpected {output} in {cmd} result on node {node_name}: {res}"

    def execute_command_on_node_and_wait_for_output(self, cmd, node_name, expected_output):
        from utility.utility import get_retry_count_and_interval
        import time
        
        retry_count, retry_interval = get_retry_count_and_interval()
        for i in range(retry_count):
            logging(f"Waiting for command {cmd} on node {node_name} returning output {expected_output} ... ({i})")
            try:
                res = NodeExec(node_name).issue_cmd(cmd)
                if expected_output in res:
                    return
            except Exception as e:
                logging(f"Execute command {cmd} on node {node_name} and wait for output {expected_output} error: {e}")
            time.sleep(retry_interval)
        
        assert False, f"Timeout waiting for output {expected_output} in {cmd} result on node {node_name}"

    def execute_command_on_node_and_get_output(self, cmd, node_name, expected_output):
        """
        Execute a command on a node and return True if the output contains the expected string, False otherwise.
        
        Args:
            cmd: Command to execute
            node_name: Name of the node
            expected_output: String to look for in the output
            
        Returns:
            True if expected_output is found in the command output, False otherwise
        """
        try:
            res = NodeExec(node_name).issue_cmd(cmd)
            return expected_output in res
        except Exception as e:
            logging(f"Execute command {cmd} on node {node_name} error: {e}")
            return False

    def execute_command_on_node_and_get_output_string(self, cmd, node_name):
        """
        Execute a command on a node and return the output as a string.
        
        Args:
            cmd: Command to execute
            node_name: Name of the node
            
        Returns:
            The command output as a string
        """
        try:
            res = NodeExec(node_name).issue_cmd(cmd)
            return res
        except Exception as e:
            logging(f"Execute command {cmd} on node {node_name} error: {e}")
            return ""

    def start_node_monitoring(self):
        """Start a background thread that monitors worker-node reachability.

        Only active when HOST_PROVIDER is 'harvester'.  Every 5 minutes the
        thread SSHs into each worker node that is *not* in the intentionally-
        powered-off set.  If SSH fails it calls power_on_node so the cloud VM
        is brought back up automatically.
        """
        if os.getenv('HOST_PROVIDER', 'vagrant') != 'harvester':
            logging('Node monitor: skipped (HOST_PROVIDER is not harvester)')
            return

        if (host_keywords._monitor_thread is not None
                and host_keywords._monitor_thread.is_alive()):
            logging('Node monitor: already running')
            return

        host_keywords._monitor_thread = threading.Thread(
            target=self._monitor_worker_nodes,
            name='NodeHealthMonitor',
            daemon=True,
        )
        host_keywords._monitor_thread.start()
        logging('Node monitor: started')

    def _monitor_worker_nodes(self):
        """Background worker: check every 5 minutes that all non-powered-off
        worker nodes are reachable via SSH; power on any that are not."""
        CHECK_INTERVAL_SECONDS = 300  # 5 minutes

        while True:
            time.sleep(CHECK_INTERVAL_SECONDS)

            try:
                worker_nodes = self.node.list_node_names_by_role('worker')
            except Exception as e:
                logging(f'Node monitor: could not list worker nodes: {e}')
                continue

            for node_name in worker_nodes:
                powered_off_nodes = BuiltIn().get_variable_value("${powered_off_nodes}") or []
                if node_name in powered_off_nodes:
                    logging(f'Node monitor: skipping {node_name} '
                            f'(intentionally powered off)')
                    continue

                try:
                    ssh_exec(node_name, 'echo alive')
                    logging(f'Node monitor: {node_name} is reachable via SSH')
                except Exception as e:
                    logging(f'Node monitor: SSH into {node_name} failed ({e}); '
                            f'attempting power on')
                    try:
                        self.host.power_on_node(node_name)
                        logging(f'Node monitor: power-on triggered for {node_name}')
                    except Exception as pe:
                        logging(f'Node monitor: failed to power on {node_name}: {pe}')

    def get_host_log_files(self, node_name, log_path):
        return self.host.get_host_log_files(node_name, log_path)

    def ssh_exec_on_node(self, node_name, cmd):
        logging(f"SSH into node {node_name} and run command: {cmd}")
        return ssh_exec(node_name, cmd)
