import pytest
import requests

from prometheus_client.parser import text_string_to_metric_families

from backupstore import set_random_backupstore  # NOQA
from common import client, core_api, volume_name  # NOQA

from common import crash_replica_processes
from common import create_pv_for_volume
from common import create_pvc_for_volume
from common import create_and_check_volume
from common import get_self_host_id
from common import wait_for_volume_degraded
from common import wait_for_volume_detached
from common import wait_for_volume_detached_unknown
from common import wait_for_volume_faulted
from common import wait_for_volume_healthy
from common import write_volume_random_data

from common import Mi
from common import LONGHORN_NAMESPACE

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


def get_metrics(core_api): # NOQA
    lht_hostId = get_self_host_id()

    pods = core_api.list_namespaced_pod(namespace=LONGHORN_NAMESPACE,
                                        label_selector="app=longhorn-manager")
    for pod in pods.items:
        if pod.spec.node_name == lht_hostId:
            manager_ip = pod.status.pod_ip
            break

    metrics = requests.get("http://{}:9500/metrics".format(manager_ip)).content
    string_data = metrics.decode('utf-8')
    result = text_string_to_metric_families(string_data)
    return result


def check_volume_metric(core_api, metric_name, metric_labels, expect_value=None): # NOQA
    metric_data = get_metrics(core_api)
    for family in metric_data:
        for sample in family.samples:
            if sample.name == metric_name:
                item = sample
                break

    assert item is not None
    assert item.labels["node"] == metric_labels["node"]
    assert item.labels["pvc"] == metric_labels["pvc"]
    assert item.labels["volume"] == metric_labels["volume"]
    assert item.labels["pvc_namespace"] == metric_labels["pvc_namespace"]
    assert type(item.value) is float
    if expect_value is not None:
        assert item.value == expect_value
    else:
        assert item.value >= 0.0


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
    write_volume_random_data(volume)
    volume = client.by_id_volume(volume_name)
    actual_size = float(volume.controllers[0].actualSize)
    capacity_szie = float(volume.size)

    metric_labels = {
        "node": lht_hostId,
        "pvc": pvc_name,
        "volume": volume_name,
        "pvc_namespace": pvc_namespace
    }

    # check volume metric basic
    check_volume_metric(core_api, "longhorn_volume_actual_size_bytes",
                        metric_labels, actual_size)
    check_volume_metric(core_api, "longhorn_volume_capacity_bytes",
                        metric_labels, capacity_szie)
    check_volume_metric(core_api, "longhorn_volume_read_throughput",
                        metric_labels)
    check_volume_metric(core_api, "longhorn_volume_write_throughput",
                        metric_labels)
    check_volume_metric(core_api, "longhorn_volume_read_iops",
                        metric_labels)
    check_volume_metric(core_api, "longhorn_volume_write_iops",
                        metric_labels)
    check_volume_metric(core_api, "longhorn_volume_read_latency",
                        metric_labels)
    check_volume_metric(core_api, "longhorn_volume_write_latency",
                        metric_labels)

    # verify longhorn_volume_robustness when volume is healthy,
    # degraded, faulted or unknown
    volume.detach()
    volume = wait_for_volume_detached_unknown(client, volume_name)
    check_volume_metric(core_api, "longhorn_volume_robustness",
                        metric_labels, longhorn_volume_robustness["unknown"])

    volume.attach(hostId=lht_hostId)
    volume = wait_for_volume_healthy(client, volume_name)
    check_volume_metric(core_api, "longhorn_volume_robustness", metric_labels,
                        longhorn_volume_robustness["healthy"])

    volume.updateReplicaCount(replicaCount=4)
    volume = wait_for_volume_degraded(client, volume_name)
    check_volume_metric(core_api, "longhorn_volume_robustness",
                        metric_labels, longhorn_volume_robustness["degraded"])

    volume.updateReplicaCount(replicaCount=3)
    volume = wait_for_volume_healthy(client, volume_name)
    crash_replica_processes(client, core_api, volume_name)
    volume = wait_for_volume_faulted(client, volume_name)

    check_volume_metric(core_api, "longhorn_volume_robustness",
                        metric_labels, longhorn_volume_robustness["faulted"])

    # verify longhorn_volume_state when volume is attached or detached
    volume = wait_for_volume_healthy(client, volume_name)
    check_volume_metric(core_api, "longhorn_volume_state", metric_labels,
                        longhorn_volume_state["attached"])

    volume.detach()
    volume = wait_for_volume_detached(client, volume_name)
    check_volume_metric(core_api, "longhorn_volume_state",
                        metric_labels, longhorn_volume_state["detached"])
