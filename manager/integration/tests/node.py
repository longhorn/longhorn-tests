import pytest

from kubernetes import client as k8sclient

from common import get_longhorn_api_client
from common import get_self_host_id


@pytest.fixture(
    params=[("foo/bar", "test", "NoSchedule"),
            ("foo", "", "NoSchedule")]
)
def taint_nodes_exclude_self(request):
    taint = k8sclient.V1Taint(
        key=request.param[0],
        value=request.param[1],
        effect=request.param[2],
    )

    self_host_id = get_self_host_id()

    api = k8sclient.CoreV1Api()
    client = get_longhorn_api_client()  # NOQA

    lh_nodes = client.list_node()
    saved_nodes = []
    for lh_node in lh_nodes:
        if lh_node.name == self_host_id:
            continue

        k8s_node = api.read_node(lh_node.name)

        saved_nodes.append(k8s_node)

        if k8s_node.spec.taints is None:
            taints = [taint]
        else:
            taints = k8s_node.spec.taints + [taint]
        payload = {
            "spec": {
                "taints": taints
            }
        }
        api.patch_node(k8s_node.metadata.name, body=payload)

    yield saved_nodes

    for node in saved_nodes:
        if node.metadata.name == self_host_id:
            continue

        if node.spec.taints is None:
            taints = []
        else:
            taints = node.spec.taints
        payload = {
            "spec": {
                "taints": taints
            }
        }
        api.patch_node(node.metadata.name, body=payload)

def taint_non_current_node(client, core_api): # NOQA
    lht_hostId = get_self_host_id()
    for node in client.list_node():
        if node.id != lht_hostId:
            taint_node_id = node.id
            break

    core_api.patch_node(taint_node_id, {
        "spec": {
            "taints":
                [{"effect": "NoSchedule",
                  "key": "key",
                  "value": "value"}]
        }
    })

    return taint_node_id
