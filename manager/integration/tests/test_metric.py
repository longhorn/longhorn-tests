import pytest
import requests
import time

from collections import defaultdict
from prometheus_client.parser import text_string_to_metric_families

from common import client, core_api, volume_name  # NOQA

from common import delete_replica_processes
from common import create_pv_for_volume
from common import create_pvc_for_volume
from common import create_snapshot
from common import create_and_check_volume
from common import generate_random_data
from common import get_self_host_id
from common import wait_for_volume_degraded
from common import wait_for_volume_detached
from common import wait_for_volume_detached_unknown
from common import wait_for_volume_expansion
from common import wait_for_volume_faulted
from common import wait_for_volume_healthy
from common import write_volume_data
from common import set_node_scheduling
from common import set_node_cordon
from common import wait_for_node_update
from common import Mi
from common import LONGHORN_NAMESPACE
from common import RETRY_COUNTS
from common import RETRY_INTERVAL
from common import DEFAULT_DISK_PATH

# The dictionaries use float type of value because the value obtained from
# prometheus_client is in float type.
# https://github.com/longhorn/longhorn-tests/pull/1531#issuecomment-1833349994
longhorn_volume_state = {
    "creating": 1.0,
    "attached": 2.0,
    "detached": 3.0,
    "attaching": 4.0,
    "detaching": 5.0,
    "deleting": 6.0,
    }

longhorn_volume_robustness = {
    "unknown": 0.0,
    "healthy": 1.0,
    "degraded": 2.0,
    "faulted": 3.0,
}


def get_metrics(core_api, metric_node_id): # NOQA
    pods = core_api.list_namespaced_pod(namespace=LONGHORN_NAMESPACE,
                                        label_selector="app=longhorn-manager")
    for pod in pods.items:
        if pod.spec.node_name == metric_node_id:
            manager_ip = pod.status.pod_ip
            break

    metrics = requests.get("http://{}:9500/metrics".format(manager_ip)).content
    string_data = metrics.decode('utf-8')
    result = text_string_to_metric_families(string_data)
    return result


def find_metric(metric_data, metric_name):
    return find_metrics(metric_data, metric_name)[0]


def find_metrics(metric_data, metric_name):
    metrics = []

    # Find the metric with the given name in the provided metric data
    for family in metric_data:
        for sample in family.samples:
            if sample.name == metric_name:
                metrics.append(sample)

    return metrics


def check_metric_with_condition(core_api, metric_name, metric_labels, expected_value=None, metric_node_id=get_self_host_id()): # NOQA)
    """
    Some metric have multiple conditions, for example metric
    longhorn_node_status have condition
    - allowScheduling
    - mountpropagation
    - ready
    - schedulable
    metric longhorn_disk_status have conditions
    - ready
    - schedulable
    Use this function to get specific condition of a mertic
    """
    metric_data = get_metrics(core_api, metric_node_id)

    found_metric = next(
        (sample for family in metric_data for sample in family.samples
            if sample.name == metric_name and
            sample.labels.get("condition") == metric_labels.get("condition")),
        None
        )

    assert found_metric is not None

    examine_metric_value(found_metric, metric_labels, expected_value)


def check_metric(core_api, metric_name, metric_labels, expected_value=None, metric_node_id=get_self_host_id()): # NOQA
    metric_data = get_metrics(core_api, metric_node_id)

    found_metric = None
    for family in metric_data:
        found_metric = next((sample for sample in family.samples if sample.name == metric_name), None) # NOQA
        if found_metric:
            break

    assert found_metric is not None

    examine_metric_value(found_metric, metric_labels, expected_value)


def examine_metric_value(found_metric, metric_labels, expected_value=None):
    for key, value in metric_labels.items():
        assert found_metric.labels[key] == value

    assert isinstance(found_metric.value, float)

    if expected_value is not None:
        assert found_metric.value == expected_value
    else:
        assert found_metric.value >= 0.0


def check_metric_sum_on_all_nodes(client, core_api, metric_name, expected_labels, expected_value=None): # NOQA
    # Initialize total_metrics to store the sum of the metric values.
    total_metrics = {"labels": defaultdict(None), "value": 0.0}

    # Initialize the total_metric_values to store the sum of the
    # metric label values.
    total_metric_values = total_metrics["labels"]

    # Find the metric based on the given labels.
    def filter_metric_by_labels(metrics, labels):
        for metric in metrics:
            is_matched = True
            for key, value in labels.items():
                if type(value) in (float, int):
                    continue

                if metric.labels[key] != value:
                    is_matched = False
                    break

            if is_matched:
                return metric

        raise AssertionError("Cannot find the metric matching the labels")

    for node in client.list_node():
        metric_data = get_metrics(core_api, node.name)

        metrics = find_metrics(metric_data, metric_name)
        if len(metrics) == 0:
            continue

        filtered_metric = filter_metric_by_labels(metrics, expected_labels)

        assert isinstance(filtered_metric.value, float)

        for key, value in expected_labels.items():
            value_type = type(value)

            if key not in total_metric_values:
                total_metric_values[key] = value_type(
                    filtered_metric.labels[key]
                )
            # Accumulate the metric label values.
            elif isinstance(value, (float, int)):
                total_metric_values[key] += value_type(
                    filtered_metric.labels[key]
                )

        # Accumulate the metric values.
        total_metrics["value"] += filtered_metric.value

    for key, value in expected_labels.items():
        assert total_metric_values[key] == value

    if expected_value is not None:
        assert total_metrics["value"] == expected_value
    else:
        assert total_metrics["value"] >= 0.0


def wait_for_metric_volume_actual_size(core_api, metric_name, metric_labels, actual_size): # NOQA
    for _ in range(RETRY_COUNTS):
        time.sleep(RETRY_INTERVAL)

        try:
            check_metric(core_api, metric_name,
                         metric_labels, actual_size)
            return
        except AssertionError:
            continue

    check_metric(core_api, metric_name,
                 metric_labels, actual_size)


def wait_for_metric_count_all_nodes(client, core_api, metric_name, metric_labels, expected_count): # NOQA
    for _ in range(RETRY_COUNTS):
        time.sleep(RETRY_INTERVAL)

        try:
            check_metric_count_all_nodes(client, core_api, metric_name,
                                         metric_labels, expected_count)
            return
        except AssertionError:
            continue

    check_metric_count_all_nodes(client, core_api, metric_name,
                                 metric_labels, expected_count)


def check_metric_count_all_nodes(client, core_api, metric_name, metric_labels, expected_count): # NOQA
    # Find the metrics based on the given labels.
    def filter_metrics_by_labels(metrics, labels):
        filtered_metrics = []
        for metric in metrics:
            is_matched = True
            for key, value in labels.items():
                if type(value) in (float, int):
                    continue

                if metric.labels[key] != value:
                    is_matched = False
                    break

            if is_matched:
                filtered_metrics.append(metric)

        print(filtered_metrics)
        return filtered_metrics

    filtered_metrics = []
    for node in client.list_node():
        metric_data = get_metrics(core_api, node.name)

        metrics = find_metrics(metric_data, metric_name)
        if len(metrics) == 0:
            continue

        filtered_metrics.extend(
            filter_metrics_by_labels(metrics, metric_labels)
        )

    assert len(filtered_metrics) == expected_count



@pytest.mark.parametrize("pvc_namespace", [LONGHORN_NAMESPACE, "default"])  # NOQA
def test_volume_metrics(client, core_api, volume_name, pvc_namespace): # NOQA
    """
    https://longhorn.io/docs/master/monitoring/metrics/#volume

    The goal of this test case is to verify that the accuracy
    of volume metrics by sending HTTP requests to
    http://{longhorn-manager IP}:9500/metrics and use
    prometheus_client to validate the return value.
    """
    lht_hostId = get_self_host_id()
    pv_name = volume_name + "-pv"
    pvc_name = volume_name + "-pvc"
    volume_size = str(500 * Mi)
    volume = create_and_check_volume(client,
                                     volume_name,
                                     num_of_replicas=3,
                                     size=volume_size)

    volume = client.by_id_volume(volume_name)
    create_pv_for_volume(client, core_api, volume, pv_name)
    create_pvc_for_volume(client, core_api, volume, pvc_name, pvc_namespace)

    volume = client.by_id_volume(volume_name)
    volume.attach(hostId=lht_hostId)
    volume = wait_for_volume_healthy(client, volume_name)
    data_size = 1 * Mi
    data = {'pos': 0,
            'len': data_size,
            'content': generate_random_data(data_size)}
    write_volume_data(volume, data)
    volume = client.by_id_volume(volume_name)
    capacity_size = float(volume.size)

    metric_labels = {
        "node": lht_hostId,
        "pvc": pvc_name,
        "volume": volume_name,
        "pvc_namespace": pvc_namespace
    }

    # check volume metric basic
    wait_for_metric_volume_actual_size(core_api,
                                       "longhorn_volume_actual_size_bytes",
                                       metric_labels, data_size)
    check_metric(core_api, "longhorn_volume_capacity_bytes",
                 metric_labels, capacity_size)
    check_metric(core_api, "longhorn_volume_read_throughput",
                 metric_labels)
    check_metric(core_api, "longhorn_volume_write_throughput",
                 metric_labels)
    check_metric(core_api, "longhorn_volume_read_iops",
                 metric_labels)
    check_metric(core_api, "longhorn_volume_write_iops",
                 metric_labels)
    check_metric(core_api, "longhorn_volume_read_latency",
                 metric_labels)
    check_metric(core_api, "longhorn_volume_write_latency",
                 metric_labels)

    # verify longhorn_volume_robustness when volume is healthy,
    # degraded, faulted or unknown
    volume.detach()
    volume = wait_for_volume_detached_unknown(client, volume_name)
    check_metric(core_api, "longhorn_volume_robustness",
                 metric_labels, longhorn_volume_robustness["unknown"])

    volume.attach(hostId=lht_hostId)
    volume = wait_for_volume_healthy(client, volume_name)
    check_metric(core_api, "longhorn_volume_robustness",
                 metric_labels, longhorn_volume_robustness["healthy"])

    volume.updateReplicaCount(replicaCount=4)
    volume = wait_for_volume_degraded(client, volume_name)
    check_metric(core_api, "longhorn_volume_robustness",
                 metric_labels, longhorn_volume_robustness["degraded"])

    volume.updateReplicaCount(replicaCount=3)
    volume = wait_for_volume_healthy(client, volume_name)
    delete_replica_processes(client, core_api, volume_name)
    volume = wait_for_volume_faulted(client, volume_name)

    check_metric(core_api, "longhorn_volume_robustness",
                 metric_labels, longhorn_volume_robustness["faulted"])

    # verify longhorn_volume_state when volume is attached or detached
    volume = wait_for_volume_healthy(client, volume_name)
    check_metric(core_api, "longhorn_volume_state",
                 metric_labels, longhorn_volume_state["attached"])

    volume.detach()
    volume = wait_for_volume_detached(client, volume_name)
    check_metric(core_api, "longhorn_volume_state",
                 metric_labels, longhorn_volume_state["detached"])


def test_metric_longhorn_snapshot_actual_size_bytes(client, core_api, volume_name): # NOQA
    """
    Scenario: test metric longhorn_snapshot_actual_size_bytes

    Issue: https://github.com/longhorn/longhorn/issues/5869

    Given a volume

    When 1 snapshot is created by user
    And 1 snapshot is created by system
    Then has a metric longhorn_snapshot_actual_size_bytes value equals to the
         size of the user created snapshot,
         and volume label is the volume name
         and user_created label is true
    And has a metric longhorn_snapshot_actual_size_bytes value equals to the
        size of the system created snapshot,
        and volume label is the volume name
        and user_created label is false

    When 3 snapshot is created by user
    Then has 4 metrics longhorn_snapshot_actual_size_bytes with
         volume label is the volume name
         and user_created label is true
    And has 1 metrics longhorn_snapshot_actual_size_bytes with
        volume label is the volume name
        and user_created label is false
    """
    self_hostId = get_self_host_id()

    # create a volume and attach it to a node.
    volume_size = 50 * Mi
    client.create_volume(name=volume_name,
                         numberOfReplicas=1,
                         size=str(volume_size))
    volume = wait_for_volume_detached(client, volume_name)
    volume.attach(hostId=self_hostId)
    volume = wait_for_volume_healthy(client, volume_name)

    # create the user snapshot.
    data_size = 10 * Mi
    user_snapshot_data_0 = {'pos': 0,
                            'len': data_size,
                            'content': generate_random_data(data_size)}
    write_volume_data(volume, user_snapshot_data_0)

    create_snapshot(client, volume_name)

    # create the system snapshot by expanding the volume.
    system_snapshot_data_0 = {'pos': 0,
                              'len': data_size,
                              'content': generate_random_data(data_size)}
    write_volume_data(volume, system_snapshot_data_0)

    volume_size_expanded_0 = str(volume_size * 2)
    volume.expand(size=volume_size_expanded_0)
    wait_for_volume_expansion(client, volume_name)
    volume = client.by_id_volume(volume_name)
    assert volume.size == volume_size_expanded_0

    # get the snapshot sizes.
    user_snapshot_size = 0
    system_snapshot_size = 0
    snapshots = volume.snapshotList()
    for snapshot in snapshots:
        if snapshot.name == "volume-head":
            continue

        if snapshot.usercreated:
            user_snapshot_size = int(snapshot.size)
        else:
            system_snapshot_size = int(snapshot.size)
    assert user_snapshot_size > 0
    assert system_snapshot_size > 0

    # assert the metric values for the user snapshot.
    user_snapshot_metric_labels = {
        "volume": volume_name,
        "user_created": "true",
    }
    check_metric_sum_on_all_nodes(client, core_api,
                                  "longhorn_snapshot_actual_size_bytes",
                                  user_snapshot_metric_labels,
                                  user_snapshot_size)

    # assert the metric values for the system snapshot.
    system_snapshot_metric_labels = {
        "volume": volume_name,
        "user_created": "false",
    }
    check_metric_sum_on_all_nodes(client, core_api,
                                  "longhorn_snapshot_actual_size_bytes",
                                  system_snapshot_metric_labels,
                                  system_snapshot_size)

    # create 3 more user snapshots.
    create_snapshot(client, volume_name)
    create_snapshot(client, volume_name)
    create_snapshot(client, volume_name)

    wait_for_metric_count_all_nodes(client, core_api,
                                    "longhorn_snapshot_actual_size_bytes",
                                    user_snapshot_metric_labels, 4)
    wait_for_metric_count_all_nodes(client, core_api,
                                    "longhorn_snapshot_actual_size_bytes",
                                    system_snapshot_metric_labels, 1)


def test_node_metrics(client, core_api): # NOQA
    lht_hostId = get_self_host_id()
    node = client.by_id_node(lht_hostId)
    disks = node.disks
    for _, disk in iter(disks.items()):
        if disk.path == DEFAULT_DISK_PATH:
            default_disk = disk
            break
    assert default_disk is not None

    metric_labels = {}
    check_metric(core_api, "longhorn_node_count_total",
                 metric_labels, expected_value=3.0)

    metric_labels = {
        "node": lht_hostId,
    }
    check_metric(core_api, "longhorn_node_cpu_capacity_millicpu",
                 metric_labels)
    check_metric(core_api, "longhorn_node_cpu_usage_millicpu",
                 metric_labels)
    check_metric(core_api, "longhorn_node_memory_capacity_bytes",
                 metric_labels)
    check_metric(core_api, "longhorn_node_memory_usage_bytes",
                 metric_labels)
    check_metric(core_api, "longhorn_node_storage_capacity_bytes",
                 metric_labels, default_disk.storageMaximum)
    check_metric(core_api, "longhorn_node_storage_usage_bytes",
                 metric_labels)
    check_metric(core_api, "longhorn_node_storage_reservation_bytes",
                 metric_labels, default_disk.storageReserved)

    # check longhorn_node_status by 4 different conditions
    metric_labels = {
        "condition": "mountpropagation",
        "condition_reason": "",
        "node": lht_hostId
    }
    check_metric_with_condition(core_api, "longhorn_node_status",
                                metric_labels, 1.0)

    metric_labels = {
        "condition": "ready",
        "condition_reason": "",
        "node": lht_hostId
    }
    check_metric_with_condition(core_api, "longhorn_node_status",
                                metric_labels, 1.0)

    metric_labels = {
        "condition": "allowScheduling",
        "condition_reason": "",
        "node": lht_hostId,
    }
    check_metric_with_condition(core_api, "longhorn_node_status",
                                metric_labels, 1.0)
    node = client.by_id_node(lht_hostId)
    set_node_scheduling(client, node, allowScheduling=False, retry=True)
    check_metric_with_condition(core_api, "longhorn_node_status",
                                metric_labels, 0.0)

    metric_labels = {
        "condition": "schedulable",
        "condition_reason": "",
        "node": lht_hostId
    }
    check_metric_with_condition(core_api, "longhorn_node_status",
                                metric_labels, 1.0)

    metric_labels = {
        "condition": "schedulable",
        "condition_reason": "KubernetesNodeCordoned",
        "node": lht_hostId
    }
    set_node_cordon(core_api, lht_hostId, True)
    wait_for_node_update(client, lht_hostId, "allowScheduling", False)
    check_metric_with_condition(core_api, "longhorn_node_status",
                                metric_labels, 0.0)
