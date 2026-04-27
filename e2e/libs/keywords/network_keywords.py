import time

from network.network import setup_control_plane_network_latency
from network.network import cleanup_control_plane_network_latency
from network.network import disconnect_node_network, disconnect_pod_network
from network.network import drop_pod_egress_traffic

from utility.utility import logging

from workload.pod import wait_for_pod_status


class network_keywords:

    def setup_control_plane_network_latency(self, latency_in_ms):
        logging(f"Setting up control plane network latency to {latency_in_ms} ms")
        setup_control_plane_network_latency(int(latency_in_ms))

    def cleanup_control_plane_network_latency(self):
        logging(f"Cleaning up control plane network latency")
        cleanup_control_plane_network_latency()

    def disconnect_node_network(self, node_name, disconnection_time_in_sec, port_number=None, wait=True):
        return disconnect_node_network(node_name, int(disconnection_time_in_sec), port_number, wait)

    def disconnect_pod_network(self, pod_name, disconnection_time_in_sec, port_number=None, wait=True):
        return disconnect_pod_network(pod_name, int(disconnection_time_in_sec), port_number, wait)

    def disconnect_network_on_nodes(self, disconnection_time_in_sec, node_list):
        logging(f'Disconnecting network on nodes {node_list} with disconnection time {disconnection_time_in_sec} seconds')

        pod_list = []
        for node_name in node_list:
            pod_name = disconnect_node_network(node_name, int(disconnection_time_in_sec), wait=False)
            pod_list.append(pod_name)

        time.sleep(int(disconnection_time_in_sec))

        for pod_name in pod_list:
            wait_for_pod_status(pod_name, "Succeeded")
        logging(f"All networks on nodes {node_list} are recovered after disconnection time {disconnection_time_in_sec} seconds")

    def drop_pod_egress_traffic(self, pod_name, drop_time_in_sec):
        drop_pod_egress_traffic(pod_name, drop_time_in_sec)

    def wait_for_block_network_pod_completed(self, pod_name, status, namespace='default'):
        wait_for_pod_status(pod_name, status, namespace)
