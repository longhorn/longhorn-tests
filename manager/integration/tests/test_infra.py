import os
import pytest
import time

from digitalocean import digitalocean
from common import get_core_api_client, get_longhorn_api_client
from common import RETRY_COUNTS, RETRY_INTERVAL


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


@pytest.yield_fixture
def reset_cluster_ready_status():
    yield
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

                node_up_k8s = wait_for_node_up_k8s(node_name, k8s_api_client)

                assert node_up_k8s

            else:
                continue

            node_up_longhorn = wait_for_node_up_longhorn(node_name,
                                                         longhorn_api_client)

            assert node_up_longhorn


@pytest.mark.infra
def test_offline_node(reset_cluster_ready_status):
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
