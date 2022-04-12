import pytest

import math
import requests
import time

from common import apps_api  # NOQA
from common import client  # NOQA
from common import core_api  # NOQA
from common import make_deployment_cpu_request  # NOQA
from common import pod_make  # NOQA
from common import volume_name  # NOQA

from common import get_longhorn_api_client
from common import get_self_host_id
from common import update_setting

from common import create_and_check_volume
from common import create_and_wait_deployment
from common import create_and_wait_pod
from common import create_pv_for_volume
from common import create_pvc_for_volume
from common import create_pvc_spec
from common import delete_and_wait_pod
from common import generate_random_data
from common import read_volume_data
from common import set_node_cordon
from common import wait_for_volume_detached
from common import wait_for_volume_healthy
from common import write_pod_volume_data

from common import Ki

from common import K8S_CLUSTER_AUTOSCALER_EVICT_KEY
from common import K8S_CLUSTER_AUTOSCALER_SCALE_DOWN_DISABLED_KEY
from common import RETRY_AUTOSCALER_COUNTS
from common import RETRY_AUTOSCALER_INTERVAL
from common import SETTING_K8S_CLUSTER_AUTOSCALER_ENABLED
from common import SETTING_REPLICA_REPLENISHMENT_WAIT_INTERVAL

CPU_REQUEST = 150


@pytest.mark.skip(reason="require K8s cluster-autoscaler")
@pytest.mark.cluster_autoscaler  # NOQA
def test_cluster_autoscaler(client, core_api, apps_api, make_deployment_cpu_request, request):  # NOQA
    """
    Scenario: Test CA

    Given Cluster with Kubernetes cluster-autoscaler.
    And Longhorn installed.
    And Set `kubernetes-cluster-autoscaler-enabled` to `true`.
    And Create deployment with cpu request.

    When Trigger CA to scale-up by increase deployment replicas.
         (double the node number, not including host node)
    Then Cluster should have double the node number.

    When Trigger CA to scale-down by decrease deployment replicas.
    Then Cluster should scale-down to original node number.
    """
    # Cleanup
    def finalizer():
        configure_node_scale_down(core_api, client.list_node(), disable="")
    request.addfinalizer(finalizer)

    host_id = get_self_host_id()
    host_node = client.by_id_node(host_id)
    configure_node_scale_down(core_api, [host_node], disable="true")
    set_node_cordon(core_api, host_id, True)

    update_setting(client, SETTING_K8S_CLUSTER_AUTOSCALER_ENABLED, "true")

    nodes = client.list_node()
    scale_size = len(nodes)-1

    scale_up_replica = get_replica_count_to_scale_up(
        core_api, scale_size, CPU_REQUEST
    )

    deployment_name = "ca-scaling-control"
    deployment = make_deployment_cpu_request(deployment_name, CPU_REQUEST)
    create_and_wait_deployment(apps_api, deployment)

    deployment["spec"]["replicas"] = scale_up_replica
    apps_api.patch_namespaced_deployment(body=deployment,
                                         namespace='default',
                                         name=deployment_name)

    wait_cluster_autoscale_up(client, nodes, scale_size)

    scale_down_replica = 0
    deployment["spec"]["replicas"] = scale_down_replica
    apps_api.patch_namespaced_deployment(body=deployment,
                                         namespace='default',
                                         name=deployment_name)
    nodes = client.list_node()
    client = wait_cluster_autoscale_down(client, core_api, nodes, scale_size)


@pytest.mark.skip(reason="require K8s cluster-autoscaler")
@pytest.mark.cluster_autoscaler  # NOQA
def test_cluster_autoscaler_all_nodes_with_volume_replicas(client, core_api, apps_api, make_deployment_cpu_request, volume_name, pod_make, request):  # NOQA
    """
    Scenario: Test CA scale down all nodes with volume replicas

    Given Cluster with Kubernetes cluster-autoscaler.
    And Longhorn installed.
    And Set `kubernetes-cluster-autoscaler-enabled` to `true`.
    And Create volume.
    And Attach the volume.
    And Write some data to volume.
    And Detach the volume.
    And Create deployment with cpu request.

    When Trigger CA to scale-up by increase deployment replicas.
         (double the node number, not including host node)
    Then Cluster should have double the node number.

    When Annotate new nodes with
         `cluster-autoscaler.kubernetes.io/scale-down-disabled`.
         (this ensures scale-down only the old nodes)
    And Trigger CA to scale-down by decrease deployment replicas.
    Then Cluster should have original node number + 1 blocked node.

    When Attach the volume to a new node. This triggers replica rebuild.
    And Volume data should be the same.
    And Detach the volume.
    Then Cluster should scale-down to original node number.
    And Volume data should be the same.
    """
    # Cleanup
    def finalizer():
        configure_node_scale_down(core_api, client.list_node(), disable="")
    request.addfinalizer(finalizer)

    host_id = get_self_host_id()
    host_node = client.by_id_node(host_id)
    configure_node_scale_down(core_api, [host_node], disable="true")
    set_node_cordon(core_api, host_id, True)

    update_setting(client, SETTING_REPLICA_REPLENISHMENT_WAIT_INTERVAL, "0")
    update_setting(client, SETTING_K8S_CLUSTER_AUTOSCALER_ENABLED, "true")

    nodes = client.list_node()
    scale_size = len(nodes)-1

    volume = create_and_check_volume(
        client, volume_name, num_of_replicas=scale_size
    )
    create_pv_for_volume(client, core_api, volume, volume.name)
    create_pvc_for_volume(client, core_api, volume, volume.name)

    pod_manifest = pod_make()
    pod_manifest['spec']['volumes'] = [create_pvc_spec(volume.name)]
    pod_name = pod_manifest['metadata']['name']
    create_and_wait_pod(core_api, pod_manifest)

    data = generate_random_data(16*Ki)
    write_pod_volume_data(core_api, pod_name, data)
    delete_and_wait_pod(core_api, pod_name)
    volume = wait_for_volume_detached(client, volume.name)

    scale_up_replica = get_replica_count_to_scale_up(
        core_api, scale_size, CPU_REQUEST
    )

    deployment_name = "autoscale-control"
    deployment = make_deployment_cpu_request(deployment_name, CPU_REQUEST)
    create_and_wait_deployment(apps_api, deployment)

    deployment["spec"]["replicas"] = scale_up_replica
    apps_api.patch_namespaced_deployment(body=deployment,
                                         namespace='default',
                                         name=deployment_name)

    wait_cluster_autoscale_up(client, nodes, scale_size)

    new_nodes = get_new_nodes(client, old_nodes=nodes)
    configure_node_scale_down(core_api, new_nodes, disable="true")

    scale_down_replica = 0
    deployment["spec"]["replicas"] = scale_down_replica
    apps_api.patch_namespaced_deployment(body=deployment,
                                         namespace='default',
                                         name=deployment_name)
    nodes = client.list_node()
    is_blocked = False
    try:
        client = wait_cluster_autoscale_down(client, core_api, nodes,
                                             scale_size)
    except AssertionError:
        client = wait_cluster_autoscale_down(client, core_api, nodes,
                                             scale_size-1)
        is_blocked = True
    assert is_blocked

    configure_node_scale_down(core_api, [new_nodes[0]], disable="")

    volume = client.by_id_volume(volume.name)
    volume = volume.attach(hostId=new_nodes[0].id)
    volume = wait_for_volume_healthy(client, volume_name)
    volume.detach(hostId="")

    client = wait_cluster_autoscale_down(client, core_api, nodes, scale_size)
    create_and_wait_pod(core_api, pod_manifest)
    resp = read_volume_data(core_api, pod_name)
    assert resp == data


def configure_node_scale_down(core_api, nodes, disable):  # NOQA
    payload = {
        "metadata": {
            "annotations": {
                K8S_CLUSTER_AUTOSCALER_SCALE_DOWN_DISABLED_KEY: disable,
            }
        }
    }
    for node in nodes:
        core_api.patch_node(node.id, body=payload)


def get_new_nodes(client, old_nodes):  # NOQA
    old_nodes_name = [n.name for n in old_nodes]
    nodes = client.list_node()
    return [n for n in nodes if not (n.name in old_nodes_name)]


def annotate_safe_to_evict_to_namespace_pods(core_api, namespace):  # NOQA
    payload = {
        "metadata": {
            "annotations": {
                K8S_CLUSTER_AUTOSCALER_EVICT_KEY: "true"
            }
        }
    }
    pods = core_api.list_namespaced_pod(namespace=namespace)
    for pod in pods.items:
        meta = pod.metadata
        try:
            key = K8S_CLUSTER_AUTOSCALER_EVICT_KEY
            if key in meta.annotations and \
                    meta.annotations[key] == "true":
                continue
        # we dont mind type error for different cloudproviders.
        except TypeError:
            pass

        core_api.patch_namespaced_pod(
            meta.name, meta.namespace, payload
        )


def get_replica_count_to_scale_up(core_api, node_number, cpu_request):  # NOQA
    host_id = get_self_host_id()
    host_kb_node = core_api.read_node(host_id)
    if host_kb_node.status.allocatable["cpu"].endswith('m'):
        allocatable_millicpu = int(host_kb_node.status.allocatable["cpu"][:-1])
    else:
        allocatable_millicpu = int(host_kb_node.status.allocatable["cpu"])*1000
    return 10 * math.ceil(allocatable_millicpu/cpu_request*node_number/10)


def wait_cluster_autoscale_up(client, nodes, diff):  # NOQA
    for _ in range(RETRY_AUTOSCALER_COUNTS):
        time.sleep(RETRY_AUTOSCALER_INTERVAL)
        check_nodes = client.list_node()
        added = len(check_nodes) - len(nodes)
        if added >= diff:
            return

    assert False, \
        f"cluster autoscaler failed to scaled up.\n" \
        f"Expect scale={diff}\n" \
        f"Got scale={added}"


def wait_cluster_autoscale_down(client, core_api, nodes, diff):  # NOQA
    for _ in range(RETRY_AUTOSCALER_COUNTS):
        time.sleep(RETRY_AUTOSCALER_INTERVAL)

        # Sometimes CA gets blocked by kube-system components
        annotate_safe_to_evict_to_namespace_pods(core_api, "kube-system")

        try:
            check_nodes = client.list_node()
        except requests.exceptions.ConnectionError:
            client = get_longhorn_api_client()
            continue

        removed = len(nodes) - len(check_nodes)
        if removed >= diff:
            return client

    assert False, \
        f"cluster autoscaler failed to scaled down.\n" \
        f"Expect scale={diff}\n" \
        f"Got scale={removed}"
