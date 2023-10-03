from network.network import setup_control_plane_network_latency
from network.network import cleanup_control_plane_network_latency
from network.network import disconnect_node_network

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
