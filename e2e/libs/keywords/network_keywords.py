from network.network import setup_control_plane_network_latency
from network.network import cleanup_control_plane_network_latency
from network.network import disconnect_node_network
from network.network import disconnect_node_network_without_waiting_completion
from workload.pod import wait_for_pod_status

from utility.utility import logging


class network_keywords:

    def setup_control_plane_network_latency(self):
        logging(f"Setting up control plane network latency")
        setup_control_plane_network_latency()

    def cleanup_control_plane_network_latency(self):
        logging(f"Cleaning up control plane network latency")
        cleanup_control_plane_network_latency()

    def disconnect_node_network(self, node_name, disconnection_time_in_sec):
        disconnect_node_network(node_name, int(disconnection_time_in_sec))

    def disconnect_node_network_without_waiting_completion(self, node_name, disconnection_time_in_sec):
        return disconnect_node_network_without_waiting_completion(node_name, int(disconnection_time_in_sec))

    def wait_for_block_network_pod_completed(self, pod_name, status, namespace='default'):
        wait_for_pod_status(pod_name, status, namespace)
