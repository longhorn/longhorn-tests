import time
import ipaddress
import requests

from kubernetes import client
from kubernetes.client.rest import ApiException
from prometheus_client.parser import text_string_to_metric_families

from node import Node
from utility.utility import get_retry_count_and_interval
from utility.utility import logging
from utility.utility import convert_size_to_bytes
import utility.constant as constant


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


def get_longhorn_metrics(node_name):
    core_api = client.CoreV1Api()
    pods = core_api.list_namespaced_pod(namespace=constant.LONGHORN_NAMESPACE, label_selector="app=longhorn-manager")
    for pod in pods.items:
        if pod.spec.node_name == node_name:
            manager_ip = pod.status.pod_ip
            break

    assert manager_ip, f"No Longhorn manager pod found on node {node_name}"

    # Handle IPv6 addresses
    ip_obj = ipaddress.ip_address(manager_ip)
    if ip_obj.version == 6:
        manager_ip = f"[{manager_ip}]"

    metrics = requests.get(f"http://{manager_ip}:9500/metrics").content
    string_data = metrics.decode('utf-8')
    result = list(text_string_to_metric_families(string_data))
    return result


def find_longhorn_metric_samples(metric_name, node_name=None):
    samples = []
    if not node_name:
        node_names = Node().list_node_names_by_role("worker")
        for node_name in node_names:
            metrics_data = get_longhorn_metrics(node_name)
            for family in metrics_data:
                for sample in family.samples:
                    if sample.name == metric_name:
                        samples.append(sample)
        logging(f"Got metric samples {metric_name}={samples} on all worker nodes")
    else:
        metrics_data = get_longhorn_metrics(node_name)
        for family in metrics_data:
            for sample in family.samples:
                if sample.name == metric_name:
                    samples.append(sample)
        logging(f"Got metric samples {metric_name}={samples} on node {node_name}")
    return samples


def check_longhorn_metric(metric_name, node_name=None, metric_label=None, expected_value=None):
    logging(f"Checking longhorn metric {locals()}")
    samples = find_longhorn_metric_samples(metric_name, node_name)
    expected_value = float(convert_size_to_bytes(expected_value))
    retry_count, retry_interval = get_retry_count_and_interval()
    if not len(samples):
        logging(f"Failed to get longhorn metric {locals()}")
        time.sleep(retry_count)
        assert False, f"Failed to get longhorn metric {locals()}"
    for sample in samples:
        if expected_value and sample.value != expected_value:
            logging(f"Expected metric {metric_name}:{metric_label} has value {expected_value}, but it's {sample.value}: {samples}")
            time.sleep(retry_count)
            assert False, f"Expected metric {metric_name}:{metric_label} has value {expected_value}, but it's {sample.value}: {samples}"
        elif float(sample.value) < 0:
            logging(f"Expected metric {metric_name}:{metric_label} > 0, but it's {sample.value}: {samples}")
            time.sleep(retry_count)
            assert False, f"Expected metric {metric_name}:{metric_label} > 0, but it's {sample.value}: {samples}"
