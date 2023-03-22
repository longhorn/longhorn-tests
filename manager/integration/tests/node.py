import pytest

from kubernetes import client as k8sclient

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
    node_items = api.list_node().items
    saved_nodes = []
    for node in node_items:
        if node.metadata.name == self_host_id:
            continue

        saved_nodes.append(node)

        if node.spec.taints is None:
            taints = [taint]
        else:
            taints = node.spec.taints + [taint]
        payload = {
            "spec": {
                "taints": taints
            }
        }
        api.patch_node(node.metadata.name, body=payload)

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
