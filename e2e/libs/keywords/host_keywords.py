from robot.libraries.BuiltIn import BuiltIn

import os

from host import Harvester, Aws, Vagrant
from host.constant import NODE_REBOOT_DOWN_TIME_SECOND

from node import Node
from node_exec import NodeExec

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

    def check_for_stuck_uninterruptible_sleep_processes_on_node(self, node_name, process_pattern, stuck_duration_seconds=30):
        """
        Check if any processes matching the pattern are stuck in uninterruptible sleep (D state).
        A process is considered stuck if it remains in D state for stuck_duration_seconds.
        
        Args:
            node_name: Name of the node to check
            process_pattern: Pattern to match processes (used with pgrep -f)
            stuck_duration_seconds: How long a process must be in D state to be considered stuck (default: 30)
        """
        import time
        
        # First check: Get all PIDs matching the pattern and their states
        cmd = f"pgrep -f '{process_pattern}' | xargs -r ps --no-headers -o pid,stat -p"
        res = NodeExec(node_name).issue_cmd(cmd)
        
        if not res or not res.strip():
            logging(f"No processes matching '{process_pattern}' found on node {node_name}")
            return
        
        # Parse output to find PIDs in D state
        d_state_pids = set()
        for line in res.strip().split('\n'):
            parts = line.strip().split()
            if len(parts) >= 2:
                pid, stat = parts[0], parts[1]
                # Check if process state starts with 'D' (uninterruptible sleep)
                if stat.startswith('D'):
                    d_state_pids.add(pid)
                    logging(f"Found process {pid} in D state on node {node_name}")
        
        if not d_state_pids:
            logging(f"No processes in D state found on node {node_name}")
            return
        
        # Wait for the specified duration
        logging(f"Found {len(d_state_pids)} process(es) in D state. Waiting {stuck_duration_seconds} seconds to check if they are stuck...")
        time.sleep(stuck_duration_seconds)
        
        # Second check: See if those same PIDs are still in D state
        res2 = NodeExec(node_name).issue_cmd(cmd)
        stuck_pids = []
        
        for line in res2.strip().split('\n'):
            parts = line.strip().split()
            if len(parts) >= 2:
                pid, stat = parts[0], parts[1]
                if stat.startswith('D') and pid in d_state_pids:
                    stuck_pids.append(pid)
        
        if stuck_pids:
            # Get full details of stuck processes
            stuck_pids_str = ' '.join(stuck_pids)
            details_cmd = f"ps --no-headers -o pid,stat,command -p {stuck_pids_str}"
            details = NodeExec(node_name).issue_cmd(details_cmd)
            error_msg = f"Found {len(stuck_pids)} process(es) stuck in D state for {stuck_duration_seconds}+ seconds on node {node_name}:\n{details}"
            logging(error_msg)
            assert False, error_msg
        else:
            logging(f"All D-state processes were transient (not stuck) on node {node_name}")

    def get_host_log_files(self, node_name, log_path):
        return self.host.get_host_log_files(node_name, log_path)
