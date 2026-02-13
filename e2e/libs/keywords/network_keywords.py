import asyncio

from network.network import setup_control_plane_network_latency
from network.network import cleanup_control_plane_network_latency
from network.network import disconnect_node_network
from network.network import disconnect_node_network_without_waiting_completion
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

    async def disconnect_node_network(self, node_name, disconnection_time_in_sec):
        disconnect_node_network(node_name, int(disconnection_time_in_sec))

    async def disconnect_network_on_nodes(self, disconnection_time_in_sec, node_list):
        logging(f'Disconnecting network on nodes {node_list} with disconnection time {disconnection_time_in_sec} seconds')

        async def disconnect_network_tasks():
            tasks = []
            for node_name in node_list:
                tasks.append(
                    asyncio.create_task(disconnect_node_network(node_name, int(disconnection_time_in_sec)), name=node_name)
                )

            done, pending = await asyncio.wait(tasks, return_when=asyncio.ALL_COMPLETED)
            for task in done:
                if task.exception():
                    assert False, task.exception()
            logging(f"All networks on nodes {node_list} are recovered after disconnection time {disconnection_time_in_sec} seconds")

        await disconnect_network_tasks()

    def disconnect_node_network_without_waiting_completion(self, node_name, disconnection_time_in_sec):
        return disconnect_node_network_without_waiting_completion(node_name, int(disconnection_time_in_sec))

    def drop_pod_egress_traffic(self, pod_name, drop_time_in_sec):
        drop_pod_egress_traffic(pod_name, drop_time_in_sec)

    def wait_for_block_network_pod_completed(self, pod_name, status, namespace='default'):
        wait_for_pod_status(pod_name, status, namespace)
