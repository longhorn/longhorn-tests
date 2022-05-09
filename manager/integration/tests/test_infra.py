import os
import pytest
import time
import subprocess

from aws import aws

from common import get_core_api_client, get_longhorn_api_client
from common import RETRY_COUNTS, RETRY_INTERVAL, RETRY_INTERVAL_LONG
from common import core_api # NOQA
from common import client # NOQA


def detect_cloudprovider():
    cloudprovider_name = os.getenv("CLOUDPROVIDER")

    if cloudprovider_name == "aws":
        cloudprovider = aws()
        return cloudprovider
    else:
        assert False


def is_node_ready_k8s(node_name, k8s_api_client):

    print(f'==> check node {node_name} is ready ...')

    node_status_k8s = k8s_api_client.read_node_status(node_name)

    for node_condition in node_status_k8s.status.conditions:
        if node_condition.type == "Ready":
            print(f'type = {node_condition.type}, '
                  f'status = {node_condition.status}')
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


def wait_for_node_down_aws(cloudprovider, node):

    aws_node_down = False
    for i in range(RETRY_COUNTS):
        if cloudprovider.instance_status(node) == 'stopped':
            aws_node_down = True
            break
        else:
            time.sleep(RETRY_INTERVAL)
            continue

    return aws_node_down


def wait_for_node_up_aws(cloudprovider, node):
    aws_node_up = False
    for i in range(RETRY_COUNTS):
        status = cloudprovider.instance_status(node)
        print(f'instance status = {status}')
        if status == 'running':
            aws_node_up = True
            break
        else:
            time.sleep(RETRY_INTERVAL_LONG)
            continue
    return aws_node_up


def is_infra_k3s():

    exec_cmd = ["kubectl", "version"]
    if "k3s" in str(subprocess.check_output(exec_cmd)):
        return True
    else:
        return False


@pytest.fixture
def reset_cluster_ready_status(request):
    yield
    node_worker_label = 'node-role.kubernetes.io/worker'
    node_controlplane_label = 'node-role.kubernetes.io/control-plane'
    node_ip_annotation = "flannel.alpha.coreos.com/public-ip"

    k8s_api_client = get_core_api_client()
    longhorn_api_client = get_longhorn_api_client()
    cloudprovider = detect_cloudprovider()

    k3s = is_infra_k3s()

    print('==> test completed! reset cluster ready status ...')

    for node_item in k8s_api_client.list_node().items:

        if k3s is True:
            if node_controlplane_label not in node_item.metadata.labels:
                node_name = node_item.metadata.name
                node_ip = node_item.metadata.annotations[node_ip_annotation]
                node = cloudprovider.instance_id_by_ip(node_ip)
            else:
                continue

        else:
            if node_worker_label in node_item.metadata.labels and \
                    node_item.metadata.labels[node_worker_label] == 'true':
                node_name = node_item.metadata.name
                node = cloudprovider.instance_id(node_name)
            else:
                continue

        if is_node_ready_k8s(node_name, k8s_api_client) is False:

            cloudprovider.instance_start(node)
            print(f'==> wait for aws node {node_name} up ...')
            aws_node_up = wait_for_node_up_aws(cloudprovider, node)
            assert aws_node_up, f'expect aws node {node_name} up'
            node_up_k8s = wait_for_node_up_k8s(node_name, k8s_api_client)

            assert node_up_k8s

        else:
            continue

        node_up_longhorn =\
            wait_for_node_up_longhorn(node_name, longhorn_api_client)

        assert node_up_longhorn


@pytest.mark.infra
@pytest.mark.order(-1)
def test_offline_node(reset_cluster_ready_status):
    """
    Test offline node

    1. Bring down one of the nodes in Kuberntes cluster (avoid current node)
    2. Make sure the Longhorn node state become `down`
    """
    node_worker_label = 'node-role.kubernetes.io/worker'
    pod_lable_selector = "longhorn-test=test-job"
    node_controlplane_label = 'node-role.kubernetes.io/control-plane'
    node_ip_annotation = "flannel.alpha.coreos.com/public-ip"

    k8s_api_client = get_core_api_client()
    longhorn_api_client = get_longhorn_api_client()
    cloudprovider = detect_cloudprovider()

    for pod in k8s_api_client.list_namespaced_pod(
                    'default',
                    label_selector=pod_lable_selector).items:
        if pod.metadata.name == "longhorn-test":
            longhorn_test_node_name = pod.spec.node_name

    k3s = is_infra_k3s()

    for node_item in k8s_api_client.list_node().items:
        if k3s is True:
            if node_controlplane_label not in node_item.metadata.labels:
                node_name = node_item.metadata.name
                node_ip = node_item.metadata.annotations[node_ip_annotation]
                if node_name == longhorn_test_node_name:
                    continue
                else:
                    node = cloudprovider.instance_id_by_ip(node_ip)
                    break
        else:
            if node_worker_label in node_item.metadata.labels and \
                    node_item.metadata.labels[node_worker_label] == 'true':
                node_name = node_item.metadata.name
                if node_name == longhorn_test_node_name:
                    continue
                else:
                    node = cloudprovider.instance_id(node_name)
                    break

    print(f'==> stop node: {node_name}')

    cloudprovider.instance_stop(node)
    wait_for_node_down_aws(cloudprovider, node)
    k8s_node_down = wait_for_node_down_k8s(node_name, k8s_api_client)

    assert k8s_node_down

    longhorn_api_client = get_longhorn_api_client()
    longhorn_node_down = wait_for_node_down_longhorn(node_name,
                                                     longhorn_api_client)

    assert longhorn_node_down
