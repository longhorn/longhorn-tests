import asyncio
from robot.libraries.BuiltIn import BuiltIn
from k8s.k8s import restart_kubelet
from k8s.k8s import delete_node
from k8s.k8s import drain_node, force_drain_node
from k8s.k8s import cordon_node, uncordon_node
from k8s.k8s import wait_all_pods_evicted
from utility.utility import logging


class k8s_keywords:

    async def restart_kubelet(self, node_name, downtime_in_sec):
        logging(f'Restarting kubelet on node {node_name} with downtime {downtime_in_sec} seconds')
        await restart_kubelet(node_name, int(downtime_in_sec))

    async def restart_kubelet_on_nodes(self, downtime_in_sec, node_list):
        logging(f'Restarting kubelet on nodes {node_list} with downtime {downtime_in_sec} seconds')

        async def restart_kubelet_tasks():
            tasks = []
            for node_name in node_list:
                tasks.append(
                    asyncio.create_task(restart_kubelet(node_name, int(downtime_in_sec)), name=node_name)
                )

            done, pending = await asyncio.wait(tasks, return_when=asyncio.ALL_COMPLETED)
            logging(f"All kubelets on nodes {node_list} are restarted after downtime {downtime_in_sec} seconds")

        await restart_kubelet_tasks()

    def delete_volume_node(self, volume_name):
        volume_keywords = BuiltIn().get_library_instance('volume_keywords')
        volume_node = volume_keywords.get_volume_node(volume_name)
        delete_node(volume_node)
        return volume_node

    def delete_replica_node(self, volume_name):
        volume_keywords = BuiltIn().get_library_instance('volume_keywords')
        replica_node = volume_keywords.get_replica_node(volume_name)
        delete_node(replica_node)
        return replica_node

    def drain_node(self, node_name):
        drain_node(node_name)

    def force_drain_node(self, node_name):
        force_drain_node(node_name)

    def uncordon_node(self, node_name):
        uncordon_node(node_name)

    def wait_for_all_pods_evicted(self, node_name):
        wait_all_pods_evicted(node_name)
