from robot.libraries.BuiltIn import BuiltIn

import asyncio

from k8s.k8s import restart_kubelet
from k8s.k8s import delete_node
from k8s.k8s import drain_node, force_drain_node
from k8s.k8s import cordon_node, uncordon_node
from k8s.k8s import wait_all_pods_evicted
from k8s.k8s import get_all_pods_on_node
from k8s.k8s import check_node_cordoned
from k8s.k8s import is_node_ready
from k8s.k8s import get_instance_manager_on_node
from k8s.k8s import check_instance_manager_pdb_not_exist
from k8s.k8s import wait_for_namespace_pods_running
from k8s.k8s import get_longhorn_node_condition_status
from k8s.k8s import set_k8s_node_zone
from k8s.k8s import verify_pod_log_after_time_contains
from k8s.k8s import deploy_system_upgrade_controller
from k8s.k8s import upgrade_k8s_to_latest_version
from k8s.k8s import patch_longhorn_component_resources_limit
from k8s.k8s import get_longhorn_component_resources_limit
from k8s.k8s import remove_longhorn_component_resources_limit
from k8s.k8s import verify_pod_log_after_time_not_contains
from k8s.k8s import is_namespaced_pods_all_running

from node import Node

from utility.utility import logging
from utility.utility import list_namespaced_pod
import utility.constant as constant


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
            for task in done:
                if task.exception():
                    assert False, task.exception()
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

    def delete_node(self, node_name):
        delete_node(node_name)

    def set_k8s_node_zone(self, node_name, zone_name):
        set_k8s_node_zone(node_name, zone_name)

    def cleanup_k8s_node_zone(self):
        nodes = Node().list_node_names_by_role("worker")
        for node in nodes:
            set_k8s_node_zone(node)

    def drain_node(self, node_name):
        drain_node(node_name)

    def force_drain_node(self, node_name):
        force_drain_node(node_name)

    def uncordon_node(self, node_name):
        uncordon_node(node_name)

    def cordon_node(self, node_name):
        cordon_node(node_name)

    def wait_for_all_pods_evicted(self, node_name):
        wait_all_pods_evicted(node_name)

    def uncordon_all_nodes(self):
        nodes = Node().list_node_names_by_role("worker")

        for node_name in nodes:
            uncordon_node(node_name)

    def get_all_pods_on_node(self, node_name):
        return get_all_pods_on_node(node_name)

    def is_node_ready(self, node_name):
        return is_node_ready(node_name)

    def check_node_cordoned(self, node_name):
        check_node_cordoned(node_name)

    def get_instance_manager_on_node(self, node_name):
        return get_instance_manager_on_node(node_name)

    def check_instance_manager_pdb_not_exist(self, instance_manager):
        return check_instance_manager_pdb_not_exist(instance_manager)

    def wait_for_namespace_pods_running(self, namespace):
        return wait_for_namespace_pods_running(namespace)

    def get_longhorn_node_condition_status(self, node_name, type):
        return get_longhorn_node_condition_status(node_name, type)

    def verify_pod_log_after_time_contains(self, pod_name, expect_log, test_start_time, namespace=constant.LONGHORN_NAMESPACE):
        return verify_pod_log_after_time_contains(pod_name, expect_log, test_start_time, namespace)

    def verify_pod_log_after_time_not_contains(self, pod_name, expect_log, test_start_time, namespace=constant.LONGHORN_NAMESPACE):
        return verify_pod_log_after_time_not_contains(pod_name, expect_log, test_start_time, namespace)

    def deploy_system_upgrade_controller(self):
        return deploy_system_upgrade_controller()

    def upgrade_k8s_to_latest_version(self, drain=False):
        return upgrade_k8s_to_latest_version(drain)

    def patch_longhorn_component_resources_limit(self, component_name, component_type, cpu_request, memory_request, cpu_limit, memory_limit, namespace=constant.LONGHORN_NAMESPACE):
        return patch_longhorn_component_resources_limit(component_name, component_type, cpu_request, memory_request, cpu_limit, memory_limit, namespace)

    def get_longhorn_component_resources_limit(self, component_name, component_type, namespace=constant.LONGHORN_NAMESPACE):
        return get_longhorn_component_resources_limit(component_name, component_type, namespace)

    def remove_longhorn_component_resources_limit(self, component_name, component_type, namespace=constant.LONGHORN_NAMESPACE):
        return remove_longhorn_component_resources_limit(component_name, component_type, namespace)

    def get_longhorn_manager_pods(self):
        pods = list_namespaced_pod(
            namespace=constant.LONGHORN_NAMESPACE,
            label_selector=f"app=longhorn-manager"
        )
        result = []
        for pod in pods:
            result.append(pod.metadata.name)
        return result

    def is_namespaced_pods_all_running(self, namespace):
        return is_namespaced_pods_all_running(namespace)
