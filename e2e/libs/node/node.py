import os
import time

from kubernetes import client

from robot.libraries.BuiltIn import BuiltIn

from utility.utility import get_retry_count_and_interval

#TODO
# it seems that Node not need to be a class
# it's just a collection of utility functions
class Node:

    def __init__(self):
        pass

    def get_all_pods_on_node(self, node_name):
        api = client.CoreV1Api()
        all_pods = api.list_namespaced_pod(namespace='longhorn-system', field_selector='spec.nodeName=' + node_name)
        user_pods = [p for p in all_pods.items if (p.metadata.namespace != 'kube-system')]
        return user_pods

    def wait_all_pods_evicted(self, node_name):
        retry_count, retry_interval = get_retry_count_and_interval()
        for _ in range(retry_count):
            pods = self.get_all_pods_on_node(node_name)
            evicted = True
            for pod in pods:
                # check non DaemonSet Pods are evicted or terminating (deletionTimestamp != None)
                pod_type = pod.metadata.owner_references[0].kind
                pod_delete_timestamp = pod.metadata.deletion_timestamp

                if pod_type != 'DaemonSet' and pod_delete_timestamp == None:
                    evicted = False
                    break

            if evicted:
                break

            time.sleep(retry_interval)

        assert evicted, 'failed to evict pods'

    def get_node_by_index(self, index, role="worker"):
        nodes = self.list_node_names_by_role(role)
        return nodes[int(index)]

    def get_node_by_name(self, node_name):
        core_api = client.CoreV1Api()
        return core_api.read_node(node_name)

    def get_test_pod_running_node(self):
        if "NODE_NAME" in os.environ:
            return os.environ["NODE_NAME"]
        else:
            return self.get_node_by_index(0)

    def get_test_pod_not_running_node(self):
        worker_nodes = self.list_node_names_by_role("worker")
        test_pod_running_node = self.get_test_pod_running_node()
        for worker_node in worker_nodes:
            if worker_node != test_pod_running_node:
                return worker_node

    def get_node_cpu_cores(self, node_name):
        node = self.get_node_by_name(node_name)
        return node.status.capacity['cpu']

    def list_node_names_by_volumes(self, volume_names):
        volume_keywords = BuiltIn().get_library_instance('volume_keywords')
        volume_nodes = {}
        for volume_name in volume_names:
            volume_node = volume_keywords.get_node_id_by_replica_locality(volume_name, "volume node")
            if volume_node not in volume_nodes:
                volume_nodes[volume_node] = True
        return list(volume_nodes.keys())

    def list_node_names_by_role(self, role="all"):
        if role not in ["all", "control-plane", "worker"]:
            raise ValueError("Role must be one of 'all', 'master' or 'worker'")

        def filter_nodes(nodes, condition):
            return [node.metadata.name for node in nodes if condition(node)]

        core_api = client.CoreV1Api()
        nodes = core_api.list_node().items

        control_plane_labels = ['node-role.kubernetes.io/master', 'node-role.kubernetes.io/control-plane']

        if role == "all":
            return sorted(filter_nodes(nodes, lambda node: True))

        if role == "control-plane":
            condition = lambda node: all(label in node.metadata.labels for label in control_plane_labels)
            return sorted(filter_nodes(nodes, condition))

        if role == "worker":
            condition = lambda node: not any(label in node.metadata.labels for label in control_plane_labels)
            return sorted(filter_nodes(nodes, condition))
