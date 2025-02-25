import time

from kubernetes import client
from kubernetes.client.rest import ApiException

from utility.utility import get_retry_count_and_interval
from utility.utility import logging

def get_node_metrics(node_name, metrics_name):
    retry_count, retry_interval = get_retry_count_and_interval()
    for i in range(retry_count):
        api = client.CustomObjectsApi()
        try:
            node_metrics = api.list_cluster_custom_object("metrics.k8s.io", "v1beta1", "nodes")
            for node in node_metrics['items']:
                if node_name == node['metadata']['name']:
                    logging(f"Got node {node_name} metrics {metrics_name} = {node['usage'][metrics_name]}")
                    return node['usage'][metrics_name]
        except ApiException as e:
            logging(f"Failed to get node {node_name} metrics {metrics_name}: {e}")
        time.sleep(retry_interval)
    assert False, f"Failed to get node {node_name} metrics {metrics_name}"
