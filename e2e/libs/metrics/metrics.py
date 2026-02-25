import time
import ipaddress
import requests
import re

from kubernetes import client
from kubernetes.client.rest import ApiException
from prometheus_client.parser import text_string_to_metric_families
from robot.libraries.BuiltIn import BuiltIn

from node import Node
from utility.utility import get_retry_count_and_interval
from utility.utility import logging
from utility.utility import convert_size_to_bytes
from utility.utility import subprocess_exec_cmd
from utility.utility import get_longhorn_namespace
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


def cpu_to_millicores(cpu):
    CPU_RE = re.compile(r"^(\d+(?:\.\d+)?)(n|u|m)?$")
    cpu = cpu.strip()
    m = CPU_RE.match(cpu)
    val = int(m.group(1))
    unit = m.group(2) or ""

    if unit == "m":
        return val
    elif unit == "u":
        return val/1000
    elif unit == "n":
        return val/1000000
    else:
        return val*1000


def mem_to_mi(mem):
    MEM_RE = re.compile(r"^(\d+(?:\.\d+)?)(Ki|Mi|Gi)?$", re.IGNORECASE)
    mem = mem.strip()
    m = MEM_RE.match(mem)
    val = int(m.group(1))
    unit = (m.group(2) or "Mi").lower()

    if unit == "ki":
        return val / 1024
    elif unit == "mi":
        return val
    elif unit == "gi":
        return val * 1024


def get_longhorn_components_memory_cpu_usage():
    cmd = f"kubectl top pod -n {get_longhorn_namespace()} --no-headers"
    output = subprocess_exec_cmd(cmd)
    # skip empty lines
    lines = [ln.strip() for ln in output.splitlines() if ln.strip()]
    # split each line by whitespace
    rows = []
    for ln in lines:
        rows.append(ln.split())
    # parse each row to dict {"name": {"cpu": cpu_m, "memory": mem_mi}}
    dict = {}
    for cols in rows:
        name = cols[0]
        cpu = cpu_to_millicores(cols[1])
        mem = mem_to_mi(cols[2])
        if name.startswith("bim"):
            name = "backing-image-manager"
        elif name.startswith("csi-attacher"):
            name = "csi-attacher"
        elif name.startswith("csi-provisioner"):
            name = "csi-provisioner"
        elif name.startswith("csi-resizer"):
            name = "csi-resizer"
        elif name.startswith("csi-snapshotter"):
            name = "csi-snapshotter"
        elif name.startswith("engine-image"):
            name = "engine-image"
        elif name.startswith("instance-manager"):
            cmd = f"kubectl get pods {name} -n {get_longhorn_namespace()} -o jsonpath='{{.metadata.labels.longhorn\\.io/data-engine}}'"
            data_engine = subprocess_exec_cmd(cmd)
            name = f"instance-manager-{data_engine}"
        elif name.startswith("longhorn-csi-plugin"):
            name = "longhorn-csi-plugin"
        elif name.startswith("longhorn-driver-deployer"):
            name = "longhorn-driver-deployer"
        elif name.startswith("longhorn-manager"):
            name = "longhorn-manager"
        elif name.startswith("longhorn-ui"):
            name = "longhorn-ui"
        elif name.startswith("share-manager"):
            name = "share-manager"

        if name not in dict:
            dict[name] = {"cpu": cpu, "memory": mem}
        else:
            dict[name]["cpu"] = max(dict[name]["cpu"], cpu)
            dict[name]["memory"] = max(dict[name]["memory"], mem)

    current = BuiltIn().get_variable_value("${LONGHORN_COMPONENTS_RESOURCE_USAGE}", None)
    if current is None:
        BuiltIn().set_global_variable("${LONGHORN_COMPONENTS_RESOURCE_USAGE}", dict)

    return dict


def is_high_resource_consumption(name, res, new_val, old_val):
    criteria = 1000 if res == "memory" else 2000
    unit = "mi" if res == "memory" else "m"
    if new_val > criteria:
        logging(f"Unexpected high {res} consumption for {name}: {new_val}{unit}. At the beginning of the test, it's only {old_val}{unit}")
        retry_count, _ = get_retry_count_and_interval()
        time.sleep(retry_count)
        assert False, f"Unexpected high {res} consumption for {name}: {new_val}{unit}. At the beginning of the test, it's only {old_val}{unit}"


def check_longhorn_components_memory_cpu_usage():
    usage = get_longhorn_components_memory_cpu_usage()
    old_usage = BuiltIn().get_variable_value("${LONGHORN_COMPONENTS_RESOURCE_USAGE}")

    logging(f"old resource usage: {old_usage}")
    logging(f"current resource usage: {usage}")

    if "backing-image-manager" in usage and "backing-image-manager" in old_usage:
        is_high_resource_consumption("backing-image-manager", "cpu",
            usage["backing-image-manager"]["cpu"],
            old_usage["backing-image-manager"]["cpu"])
        is_high_resource_consumption("backing-image-manager", "memory",
            usage["backing-image-manager"]["memory"],
            cold_usage["backing-image-manager"]["memory"])

    is_high_resource_consumption("csi-attacher", "cpu",
        usage["csi-attacher"]["cpu"],
        old_usage["csi-attacher"]["cpu"])
    is_high_resource_consumption("csi-attacher", "memory",
        usage["csi-attacher"]["memory"],
        old_usage["csi-attacher"]["memory"])

    is_high_resource_consumption("csi-provisioner", "cpu",
        usage["csi-provisioner"]["cpu"],
        old_usage["csi-provisioner"]["cpu"])
    is_high_resource_consumption("csi-provisioner", "memory",
        usage["csi-provisioner"]["memory"],
        old_usage["csi-provisioner"]["memory"])

    is_high_resource_consumption("csi-resizer", "cpu",
        usage["csi-resizer"]["cpu"],
        old_usage["csi-resizer"]["cpu"])
    is_high_resource_consumption("csi-resizer", "memory",
        usage["csi-resizer"]["memory"],
        old_usage["csi-resizer"]["memory"])

    is_high_resource_consumption("csi-snapshotter", "cpu",
        usage["csi-snapshotter"]["cpu"],
        old_usage["csi-snapshotter"]["cpu"])
    is_high_resource_consumption("csi-snapshotter", "memory",
        usage["csi-snapshotter"]["memory"],
        old_usage["csi-snapshotter"]["memory"])

    is_high_resource_consumption("engine-image", "cpu",
        usage["engine-image"]["cpu"],
        old_usage["engine-image"]["cpu"])
    is_high_resource_consumption("engine-image", "memory",
        usage["engine-image"]["memory"],
        old_usage["engine-image"]["memory"])

    is_high_resource_consumption("instance-manager-v1", "cpu",
        usage["instance-manager-v1"]["cpu"],
        old_usage["instance-manager-v1"]["cpu"])
    is_high_resource_consumption("instance-manager-v1", "memory",
        usage["instance-manager-v1"]["memory"],
        old_usage["instance-manager-v1"]["memory"])

    if "instance-manager-v2" in usage and "instance-manager-v2" in old_usage:
        is_high_resource_consumption("instance-manager-v2", "cpu",
            usage["instance-manager-v2"]["cpu"],
            old_usage["instance-manager-v2"]["cpu"])
        is_high_resource_consumption("instance-manager-v2", "memory",
            usage["instance-manager-v2"]["memory"],
            old_usage["instance-manager-v2"]["memory"])

    is_high_resource_consumption("longhorn-csi-plugin", "cpu",
        usage["longhorn-csi-plugin"]["cpu"],
        old_usage["longhorn-csi-plugin"]["cpu"])
    is_high_resource_consumption("longhorn-csi-plugin", "memory",
        usage["longhorn-csi-plugin"]["memory"],
        old_usage["longhorn-csi-plugin"]["memory"])

    is_high_resource_consumption("longhorn-driver-deployer", "cpu",
        usage["longhorn-driver-deployer"]["cpu"],
        old_usage["longhorn-driver-deployer"]["cpu"])
    is_high_resource_consumption("longhorn-driver-deployer", "memory",
        usage["longhorn-driver-deployer"]["memory"],
        old_usage["longhorn-driver-deployer"]["memory"])

    is_high_resource_consumption("longhorn-manager", "cpu",
        usage["longhorn-manager"]["cpu"],
        old_usage["longhorn-manager"]["cpu"])
    is_high_resource_consumption("longhorn-manager", "memory",
        usage["longhorn-manager"]["memory"],
        old_usage["longhorn-manager"]["memory"])

    is_high_resource_consumption("longhorn-ui", "cpu",
        usage["longhorn-ui"]["cpu"],
        old_usage["longhorn-ui"]["cpu"])
    is_high_resource_consumption("longhorn-ui", "memory",
        usage["longhorn-ui"]["memory"],
        old_usage["longhorn-ui"]["memory"])

    if "share-manager" in usage and "share-manager" in old_usage:
        is_high_resource_consumption("share-manager", "cpu",
            usage["share-manager"]["cpu"],
            old_usage["share-manager"]["cpu"])
        is_high_resource_consumption("share-manager", "memory",
            usage["share-manager"]["memory"],
            old_usage["share-manager"]["memory"])
