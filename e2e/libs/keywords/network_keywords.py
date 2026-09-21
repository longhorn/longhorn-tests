import time

from network.network import setup_control_plane_network_latency
from network.network import cleanup_control_plane_network_latency
from network.network import disconnect_node_network, disconnect_pod_network
from network.network import drop_pod_egress_traffic
from network.network import drop_tcp_connection_replies
from network.network import get_pod_tcp_connections
from network.network import limit_pod_traffic_to_ip
from network.network import remove_pod_traffic_limit

from replica import Replica

from utility.utility import get_retry_count_and_interval
from utility.utility import logging

from workload.pod import wait_for_pod_status


class network_keywords:

    def __init__(self):
        self.replica = Replica()
        self.retry_count, self.retry_interval = \
            get_retry_count_and_interval()

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

    def limit_v1_replica_rebuild_traffic(self, volume_name,
                                         source_node_name,
                                         target_node_name, rate_in_mbit):
        source_replica = self._get_running_replica(
            volume_name, source_node_name)
        target_replica = self._get_running_replica(
            volume_name, target_node_name)

        context = {
            "source_instance_manager":
                source_replica["status"]["instanceManagerName"],
            "source_ip": source_replica["status"]["ip"],
            "source_sync_agent_port":
                int(source_replica["status"]["port"]) + 2,
            "target_ip": target_replica["status"]["ip"],
        }
        context["interface"] = limit_pod_traffic_to_ip(
            context["source_instance_manager"],
            context["target_ip"],
            context["source_sync_agent_port"],
            int(rate_in_mbit),
        )
        return context

    def cleanup_v1_replica_rebuild_traffic(self, context):
        remove_pod_traffic_limit(
            context["source_instance_manager"], context["interface"])

    def find_file_send_connection(self, context):
        for i in range(self.retry_count):
            connections = get_pod_tcp_connections(
                context["source_instance_manager"])
            for connection in connections:
                if self._is_file_send_connection(connection, context):
                    connection["pod_name"] = \
                        context["source_instance_manager"]
                    logging(f"Found FileSend TCP connection {connection}")
                    return connection
            logging(f"Waiting for FileSend TCP connection ... ({i})")
            time.sleep(self.retry_interval)

        assert False, (
            "Failed to find FileSend TCP connection from target "
            f"{context['target_ip']} to source "
            f"{context['source_ip']}:"
            f"{context['source_sync_agent_port']}"
        )

    def drop_file_send_connection_replies(self, connection,
                                          drop_time_in_sec):
        drop_tcp_connection_replies(
            connection["pod_name"], connection, int(drop_time_in_sec))

    def assert_file_send_connection_established(self, connection):
        connections = get_pod_tcp_connections(connection["pod_name"])
        assert self._connection_in_list(connection, connections), (
            "FileSend TCP connection is no longer established: "
            f"{connection}"
        )

    def _get_running_replica(self, volume_name, node_name):
        replicas = [
            replica for replica in self.replica.get(volume_name, node_name)
            if replica.get("status", {}).get("currentState") == "running"
        ]
        assert len(replicas) == 1, (
            f"Expected one running replica for volume {volume_name} on "
            f"node {node_name}, got {len(replicas)}"
        )
        return replicas[0]

    @staticmethod
    def _is_file_send_connection(connection, context):
        return (
            connection["local_ip"] == context["source_ip"] and
            connection["local_port"] ==
            context["source_sync_agent_port"] and
            connection["remote_ip"] == context["target_ip"]
        )

    @staticmethod
    def _connection_in_list(expected, connections):
        fields = ("local_ip", "local_port", "remote_ip", "remote_port")
        return any(
            all(connection[field] == expected[field] for field in fields)
            for connection in connections
        )
