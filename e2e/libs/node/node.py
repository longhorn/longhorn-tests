import boto3
import time
import yaml

from kubernetes import client

from node.utility import list_node_names_by_role

from utility.utility import logging
from utility.utility import wait_for_cluster_ready


class Node:

    def __init__(self):
        with open('/tmp/instance_mapping', 'r') as f:
            self.mapping = yaml.safe_load(f)
        self.aws_client = boto3.client('ec2')

    def reboot_all_nodes(self, shut_down_time_in_sec=60):
        instance_ids = [value for value in self.mapping.values()]

        resp = self.aws_client.stop_instances(InstanceIds=instance_ids)
        logging(f"Stopping instances {instance_ids} response: {resp}")
        waiter = self.aws_client.get_waiter('instance_stopped')
        waiter.wait(InstanceIds=instance_ids)
        logging(f"Stopped instances")

        time.sleep(shut_down_time_in_sec)

        resp = self.aws_client.start_instances(InstanceIds=instance_ids)
        logging(f"Starting instances {instance_ids} response: {resp}")
        waiter = self.aws_client.get_waiter('instance_running')
        waiter.wait(InstanceIds=instance_ids)
        wait_for_cluster_ready()
        logging(f"Started instances")

    def reboot_node(self, reboot_node_name, shut_down_time_in_sec=60):
        instance_ids = [self.mapping[reboot_node_name]]

        resp = self.aws_client.stop_instances(InstanceIds=instance_ids)
        logging(f"Stopping instances {instance_ids} response: {resp}")
        waiter = self.aws_client.get_waiter('instance_stopped')
        waiter.wait(InstanceIds=instance_ids)
        logging(f"Stopped instances")

        time.sleep(shut_down_time_in_sec)

        resp = self.aws_client.start_instances(InstanceIds=instance_ids)
        logging(f"Starting instances {instance_ids} response: {resp}")
        waiter = self.aws_client.get_waiter('instance_running')
        waiter.wait(InstanceIds=instance_ids)
        logging(f"Started instances")

    def reboot_all_worker_nodes(self, shut_down_time_in_sec=60):
        instance_ids = [self.mapping[value] for value in list_node_names_by_role("worker")]

        resp = self.aws_client.stop_instances(InstanceIds=instance_ids)
        logging(f"Stopping instances {instance_ids} response: {resp}")
        waiter = self.aws_client.get_waiter('instance_stopped')
        waiter.wait(InstanceIds=instance_ids)
        logging(f"Stopped instances")

        time.sleep(shut_down_time_in_sec)

        resp = self.aws_client.start_instances(InstanceIds=instance_ids)
        logging(f"Starting instances {instance_ids} response: {resp}")
        waiter = self.aws_client.get_waiter('instance_running')
        waiter.wait(InstanceIds=instance_ids)
        logging(f"Started instances")

    def get_all_pods_on_node(self, node_name):
        api = client.CoreV1Api()
        all_pods = api.list_namespaced_pod(namespace='longhorn-system', field_selector='spec.nodeName=' + node_name)
        user_pods = [p for p in all_pods.items if (p.metadata.namespace != 'kube-system')]
        return user_pods

    def wait_all_pods_evicted(self, node_name):
        for i in range(RETRY_COUNT):
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

            time.sleep(RETRY_INTERVAL)

        assert evicted, 'failed to evict pods'
