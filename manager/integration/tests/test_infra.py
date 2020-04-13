import os
import pytest
import time

from digitalocean import digitalocean
from common import get_core_api_client, get_longhorn_api_client
from common import RETRY_COUNTS, RETRY_INTERVAL

from common import SIZE
from common import create_and_check_volume
from common import wait_for_volume_detached
from common import create_pvc_for_volume
from common import create_pv_for_volume
from common import delete_and_wait_pod
from common import make_deployment_with_pvc   # NOQA
from common import create_and_wait_deployment
from common import get_apps_api_client
from common import wait_for_volume_healthy
from common import generate_random_data
from common import VOLUME_RWTEST_SIZE
from common import write_pod_volume_data
from common import read_volume_data
from common import get_self_host_id
from common import core_api # NOQA
from common import client # NOQA
from common import wait_pod
from common import volume_name # NOQA
from common import generate_volume_name

TERMINATING_POD_RETRYS = 30
TERMINATING_POD_INTERVAL = 1


def detect_cloudprovider():
    cloudprovider_name = os.getenv("CLOUDPROVIDER")

    if cloudprovider_name == "digitalocean":
        cloudprovider = digitalocean()
        return cloudprovider
    else:
        assert False


def is_node_ready_k8s(node_name, k8s_api_client):
    node_status_k8s = k8s_api_client.read_node_status(node_name)

    for node_condition in node_status_k8s.status.conditions:
        if node_condition.type == "Ready" and \
           node_condition.status == "True":
            node_ready = True
        else:
            node_ready = False

    return node_ready


def wait_for_node_up_k8s(node_name, k8s_api_client):
    node_up = False
    for i in range(RETRY_COUNTS):
        if is_node_ready_k8s(node_name, k8s_api_client) is True:
            node_up = True
            break
        else:
            time.sleep(RETRY_INTERVAL)
            continue
    return node_up


def wait_for_node_down_k8s(node_name, k8s_api_client):
    node_down = False
    for i in range(RETRY_COUNTS):
        if is_node_ready_k8s(node_name, k8s_api_client) is False:
            node_down = True
            break
        else:
            time.sleep(RETRY_INTERVAL)
            continue
    return node_down


def is_node_ready_longhorn(node_name, longhorn_api_client):
    node = longhorn_api_client.by_id_node(node_name)

    if node.conditions.Ready.status == 'False':
        node_ready = False
    else:
        node_ready = True

    return node_ready


def wait_for_node_up_longhorn(node_name, longhorn_api_client):
    longhorn_node_up = False
    for i in range(RETRY_COUNTS):
        if is_node_ready_longhorn(node_name, longhorn_api_client) is True:
            longhorn_node_up = True
            break
        else:
            time.sleep(RETRY_INTERVAL)
            continue

    return longhorn_node_up


def wait_for_node_down_longhorn(node_name, longhorn_api_client):
    longhorn_node_down = False
    for i in range(RETRY_COUNTS):
        if is_node_ready_longhorn(node_name, longhorn_api_client) is False:
            longhorn_node_down = True
            break
        else:
            time.sleep(RETRY_INTERVAL)
            continue

    return longhorn_node_down


@pytest.fixture
def reset_cluster_ready_status(request):
    def finalizer():
        node_worker_label = 'node-role.kubernetes.io/worker'

        k8s_api_client = get_core_api_client()
        longhorn_api_client = get_longhorn_api_client()
        cloudprovider = detect_cloudprovider()

        for node_item in k8s_api_client.list_node().items:
            if node_worker_label in node_item.metadata.labels and \
                    node_item.metadata.labels[node_worker_label] == 'true':
                node_name = node_item.metadata.name

                if is_node_ready_k8s(node_name, k8s_api_client) is False:
                    node = cloudprovider.node_id(node_name)

                    cloudprovider.node_start(node)

                    node_up_k8s = wait_for_node_up_k8s(node_name,
                                                       k8s_api_client)

                    assert node_up_k8s

                else:
                    continue

                node_up_longhorn =\
                    wait_for_node_up_longhorn(node_name,
                                              longhorn_api_client)

                assert node_up_longhorn

    request.addfinalizer(finalizer)


@pytest.mark.infra
def test_offline_node(reset_cluster_ready_status):
    """
    Test offline node

    1. Bring down one of the nodes in Kuberntes cluster (avoid current node)
    2. Make sure the Longhorn node state become `down`
    """
    node_worker_label = 'node-role.kubernetes.io/worker'
    pod_lable_selector = "longhorn-test=test-job"

    k8s_api_client = get_core_api_client()
    longhorn_api_client = get_longhorn_api_client()
    cloudprovider = detect_cloudprovider()

    for pod in k8s_api_client.list_namespaced_pod(
                    'default',
                    label_selector=pod_lable_selector).items:
        if pod.metadata.name == "longhorn-test":
            longhorn_test_node_name = pod.spec.node_name

    for node_item in k8s_api_client.list_node().items:
        if node_worker_label in node_item.metadata.labels and \
                node_item.metadata.labels[node_worker_label] == 'true':
            node_name = node_item.metadata.name
            if node_name == longhorn_test_node_name:
                continue
            else:
                break

    node = cloudprovider.node_id(node_name)

    cloudprovider.node_shutdown(node)

    k8s_node_down = wait_for_node_down_k8s(node_name, k8s_api_client)

    assert k8s_node_down

    longhorn_node_down = wait_for_node_down_longhorn(node_name,
                                                     longhorn_api_client)

    assert longhorn_node_down


@pytest.mark.infra
def test_offline_node_with_attached_volume_and_pod(client, core_api, volume_name, make_deployment_with_pvc, reset_cluster_ready_status): # NOQA
    """
    Test offline node with attached volume and pod

    1. Create PV/PVC/Deployment manifest.
    2. Update deployment's tolerations to 20 seconds to speed up test
    3. Update deployment's node affinity rule to avoid the current node
    4. Create volume, PV/PVC and deployment.
    5. Find the pod in the deployment and write `test_data` into it
    6. Shutdown the node pod is running on
    7. Wait for deployment to delete the pod
        1. Deployment cannot delete the pod here because kubelet doesn't
        response
    8. Force delete the terminating pod
    9. Wait for the new pod to be created and the volume attached
    10. Check `test_data` in the new pod
    """
    toleration_seconds = 20

    apps_api = get_apps_api_client()
    cloudprovider = detect_cloudprovider()

    volume_name = generate_volume_name()
    pv_name = volume_name + "-pv"
    pvc_name = volume_name + "-pvc"
    deployment_name = volume_name + "-dep"

    longhorn_test_node_name = get_self_host_id()

    deployment_manifest = make_deployment_with_pvc(
        deployment_name,
        pvc_name
    )

    unreachable_toleration = {
        "key": "node.kubernetes.io/unreachable",
        "operator": "Exists",
        "effect": "NoExecute",
        "tolerationSeconds": toleration_seconds
    }

    not_ready_toleration = {
        "key": "node.kubernetes.io/not-ready",
        "operator": "Exists",
        "effect": "NoExecute",
        "tolerationSeconds": toleration_seconds
    }

    deployment_manifest["spec"]["template"]["spec"]["tolerations"] =\
        [unreachable_toleration, not_ready_toleration]

    node_affinity_roles = {
        "nodeAffinity": {
          "requiredDuringSchedulingIgnoredDuringExecution": {
            "nodeSelectorTerms": [
              {
                "matchExpressions": [
                  {
                    "key": "kubernetes.io/hostname",
                    "operator": "NotIn",
                    "values": [longhorn_test_node_name]
                  }
                ]
              }
            ]
          }
        }
      }

    deployment_manifest["spec"]["template"]["spec"]["affinity"] =\
        node_affinity_roles

    longhorn_volume = create_and_check_volume(
        client,
        volume_name,
        size=SIZE
    )

    wait_for_volume_detached(client, volume_name)

    create_pv_for_volume(client,
                         core_api,
                         longhorn_volume,
                         pv_name)

    create_pvc_for_volume(client,
                          core_api,
                          longhorn_volume,
                          pvc_name)

    create_and_wait_deployment(apps_api, deployment_manifest)

    deployment_label_selector =\
        "name=" + deployment_manifest["metadata"]["labels"]["name"]

    deployment_pod_list =\
        core_api.list_namespaced_pod(namespace="default",
                                     label_selector=deployment_label_selector)

    assert deployment_pod_list.items.__len__() == 1

    pod_name = deployment_pod_list.items[0].metadata.name

    test_data = generate_random_data(VOLUME_RWTEST_SIZE)

    write_pod_volume_data(core_api, pod_name, test_data)

    node_name = deployment_pod_list.items[0].spec.node_name
    node = cloudprovider.node_id(node_name)

    cloudprovider.node_shutdown(node)

    k8s_node_down = wait_for_node_down_k8s(node_name, core_api)

    assert k8s_node_down

    client = get_longhorn_api_client()

    longhorn_node_down = wait_for_node_down_longhorn(node_name,
                                                     client)
    assert longhorn_node_down

    time.sleep(toleration_seconds + 5)

    for i in range(TERMINATING_POD_RETRYS):
        deployment_pod_list =\
            core_api.list_namespaced_pod(
                namespace="default",
                label_selector=deployment_label_selector
            )

        terminating_pod_name = None
        for pod in deployment_pod_list.items:
            if pod.metadata.__getattribute__("deletion_timestamp") is not None:
                terminating_pod_name = pod.metadata.name
                break

        if terminating_pod_name is not None:
            break
        else:
            time.sleep(TERMINATING_POD_INTERVAL)

    assert terminating_pod_name is not None

    core_api.delete_namespaced_pod(namespace="default",
                                   name=terminating_pod_name,
                                   grace_period_seconds=0)

    delete_and_wait_pod(core_api, terminating_pod_name)

    deployment_pod_list =\
        core_api.list_namespaced_pod(
            namespace="default",
            label_selector=deployment_label_selector
        )

    assert deployment_pod_list.items.__len__() == 1

    wait_for_volume_detached(client, volume_name)
    wait_for_volume_healthy(client, volume_name)

    deployment_pod_list =\
        core_api.list_namespaced_pod(
            namespace="default",
            label_selector=deployment_label_selector
        )

    assert deployment_pod_list.items.__len__() == 1

    new_pod_name = deployment_pod_list.items[0].metadata.name

    wait_pod(new_pod_name)

    resp_data = read_volume_data(core_api, new_pod_name)

    assert test_data == resp_data
