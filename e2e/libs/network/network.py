from robot.libraries.BuiltIn import BuiltIn
from node import Node
from node_exec import NodeExec
from workload.pod import create_pod
from workload.pod import delete_pod
from workload.pod import new_pod_manifest
from workload.pod import IMAGE_BUSYBOX

from utility.constant import LABEL_TEST
from utility.constant import LABEL_TEST_VALUE

import time


def get_control_plane_node_network_latency_in_ms():
    latency_in_ms = int(BuiltIn().get_variable_value("${CONTROL_PLANE_NODE_NETWORK_LATENCY_IN_MS}", default="0"))
    return latency_in_ms


def setup_control_plane_network_latency():
    latency_in_ms = get_control_plane_node_network_latency_in_ms()
    if latency_in_ms != 0:
        control_plane_nodes = Node.list_node_names_by_role("control-plane")
        for control_plane_node in control_plane_nodes:
            cmd = f"tc qdisc replace dev eth0 root netem delay {latency_in_ms}ms"
            res = NodeExec.get_instance().issue_cmd(control_plane_node, cmd)
            cmd = f"tc qdisc show dev eth0 | grep delay"
            res = NodeExec.get_instance().issue_cmd(control_plane_node, cmd)
            assert res, "setup control plane network latency failed"


def cleanup_control_plane_network_latency():
    latency_in_ms = get_control_plane_node_network_latency_in_ms()
    if latency_in_ms != 0:
        control_plane_nodes = Node.list_node_names_by_role("control-plane")
        for control_plane_node in control_plane_nodes:
            cmd = "tc qdisc del dev eth0 root"
            res = NodeExec.get_instance().issue_cmd(control_plane_node, cmd)
            cmd = f"tc qdisc show dev eth0 | grep -v delay"
            res = NodeExec.get_instance().issue_cmd(control_plane_node, cmd)
            assert res, "cleanup control plane network failed"

def disconnect_node_network(node_name, disconnection_time_in_sec=10):
    manifest = new_pod_manifest(
        image=IMAGE_BUSYBOX,
        command=["nsenter", "--mount=/rootfs/proc/1/ns/mnt", "--net=/rootfs/proc/1/ns/net", "--", "sh"],
        args=["-c", f"sleep 10 && tc qdisc replace dev eth0 root netem loss 100% && sleep {disconnection_time_in_sec} && tc qdisc del dev eth0 root"],
        node_name=node_name
    )
    pod_name = manifest['metadata']['name']
    create_pod(manifest, is_wait_for_pod_running=True)

    time.sleep(disconnection_time_in_sec)

    delete_pod(pod_name)

def disconnect_node_network_without_waiting_completion(node_name, disconnection_time_in_sec=10):
    manifest = new_pod_manifest(
        image=IMAGE_BUSYBOX,
        command=["nsenter", "--mount=/rootfs/proc/1/ns/mnt", "--net=/rootfs/proc/1/ns/net", "--", "sh"],
        args=["-c", f"sleep 10 && tc qdisc replace dev eth0 root netem loss 100% && sleep {disconnection_time_in_sec} && tc qdisc del dev eth0 root"],
        node_name=node_name,
        labels = {LABEL_TEST: LABEL_TEST_VALUE}
    )
    pod_name = manifest['metadata']['name']
    create_pod(manifest, is_wait_for_pod_running=True)

    return pod_name
