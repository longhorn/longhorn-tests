import asyncio
from robot.libraries.BuiltIn import BuiltIn
from k8s.k8s import restart_kubelet
from k8s.k8s import delete_node
from k8s.k8s import drain_node, force_drain_node
from k8s.k8s import cordon_node, uncordon_node
from k8s.k8s import wait_all_pods_evicted
from k8s.k8s import get_all_pods_on_node
from k8s.k8s import check_node_cordoned
from k8s.k8s import get_instance_manager_on_node
from k8s.k8s import check_instance_manager_pdb_not_exist
from k8s.k8s import wait_for_namespace_pods_running
from utility.utility import logging
from node import Node

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
        timeout = int(BuiltIn().get_variable_value("${DRAIN_TIMEOUT}", default="90"))
        force_drain_node(node_name, timeout)

    def uncordon_node(self, node_name):
        uncordon_node(node_name)

    def cordon_node(self, node_name):
        cordon_node(node_name)

    def wait_for_all_pods_evicted(self, node_name):
        wait_all_pods_evicted(node_name)

    def uncordon_all_nodes(self):
        nodes = Node.list_node_names_by_role("worker")

        for node_name in nodes:
            uncordon_node(node_name)

    def get_all_pods_on_node(self, node_name):
        return get_all_pods_on_node(node_name)

    def check_node_cordoned(self, node_name):
        check_node_cordoned(node_name)

    def get_instance_manager_on_node(self, node_name):
        return get_instance_manager_on_node(node_name)

    def check_instance_manager_pdb_not_exist(self, instance_manager):
        return check_instance_manager_pdb_not_exist(instance_manager)

    def wait_for_namespace_pods_running(self, namespace):
        return wait_for_namespace_pods_running(namespace)
