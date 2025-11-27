import asyncio
import os

from node import Node
from node_exec import NodeExec
from node_exec.constant import HOST_ROOTFS

from robot.libraries.BuiltIn import BuiltIn

from utility.constant import LABEL_TEST
from utility.constant import LABEL_TEST_VALUE
import utility.constant as constant
from utility.utility import pod_exec

from workload.pod import create_pod
from workload.pod import delete_pod
from workload.pod import new_pod_manifest
from workload.pod import wait_for_pod_status
from workload.pod import IMAGE_BUSYBOX


def get_control_plane_node_network_latency_in_ms():
    latency_in_ms = int(BuiltIn().get_variable_value("${CONTROL_PLANE_NODE_NETWORK_LATENCY_IN_MS}", default="0"))
    return latency_in_ms


def setup_control_plane_network_latency():
    latency_in_ms = get_control_plane_node_network_latency_in_ms()
    if latency_in_ms != 0:
        control_plane_nodes = Node.list_node_names_by_role("control-plane")
        for control_plane_node in control_plane_nodes:
            cmd = f"tc qdisc replace dev eth0 root netem delay {latency_in_ms}ms"
            res = NodeExec(control_plane_node).issue_cmd(cmd)
            cmd = f"tc qdisc show dev eth0 | grep delay"
            res = NodeExec(control_plane_node).issue_cmd(cmd)
            assert res, "setup control plane network latency failed"


def cleanup_control_plane_network_latency():
    latency_in_ms = get_control_plane_node_network_latency_in_ms()
    if latency_in_ms != 0:
        control_plane_nodes = Node.list_node_names_by_role("control-plane")
        for control_plane_node in control_plane_nodes:
            cmd = "tc qdisc del dev eth0 root"
            res = NodeExec(control_plane_node).issue_cmd(cmd)
            cmd = f"tc qdisc show dev eth0 | grep -v delay"
            res = NodeExec(control_plane_node).issue_cmd(cmd)
            assert res, "cleanup control plane network failed"

async def disconnect_node_network(node_name, disconnection_time_in_sec=10):
    ns_mnt = os.path.join(HOST_ROOTFS, "proc/1/ns/mnt")
    ns_net = os.path.join(HOST_ROOTFS, "proc/1/ns/net")
    manifest = new_pod_manifest(
        image=IMAGE_BUSYBOX,
        command=["nsenter", f"--mount={ns_mnt}", f"--net={ns_net}", "--", "sh"],
        args=["-c", f"sleep 10 && tc qdisc replace dev eth0 root netem loss 100% && sleep {disconnection_time_in_sec} && tc qdisc del dev eth0 root"],
        node_name=node_name
    )
    pod_name = manifest['metadata']['name']
    create_pod(manifest, is_wait_for_pod_running=True)

    await asyncio.sleep(disconnection_time_in_sec)

    delete_pod(pod_name)

def disconnect_node_network_without_waiting_completion(node_name, disconnection_time_in_sec=10):
    ns_mnt = os.path.join(HOST_ROOTFS, "proc/1/ns/mnt")
    ns_net = os.path.join(HOST_ROOTFS, "proc/1/ns/net")
    manifest = new_pod_manifest(
        image=IMAGE_BUSYBOX,
        command=["nsenter", f"--mount={ns_mnt}", f"--net={ns_net}", "--", "sh"],
        args=["-c", f"sleep 10 && tc qdisc replace dev eth0 root netem loss 100% && sleep {disconnection_time_in_sec} && tc qdisc del dev eth0 root"],
        node_name=node_name,
        labels = {LABEL_TEST: LABEL_TEST_VALUE}
    )
    pod_name = manifest['metadata']['name']
    create_pod(manifest, is_wait_for_pod_running=True)

    return pod_name

# For now, drop_pod_egress_traffic only works in "suse-like" container images. It relies on iptables userspace 
# utilities, which must generally be installed before execution.
def drop_pod_egress_traffic(pod_name, drop_time_in_sec=10):
    wait_for_pod_status(pod_name, "Running", namespace=constant.LONGHORN_NAMESPACE)

    # Install iptables and execute the drop rule in the foreground.
    # Then, sleep and execute the undrop rule in the background.
    # Redirect stdout and stderr for the background commands so exec returns without waiting.
    # We MUST allow egress traffic from 3260, as this is the port used for communication between the iSCSI initiator and
    # tgt. If the connection between these two components is broken, the initiator will stop sending I/O to tgt and
    # tgt will stop sending I/O to the engine. Replicas cannot time out if I/O isn't flowing.
    install_cmd = 'zypper install -y iptables;'
    drop_rule = 'iptables -A OUTPUT -p tcp --sport 3260 -j ACCEPT; iptables -A OUTPUT -p tcp -j DROP;'
    undrop_rule = 'iptables -D OUTPUT -p tcp --sport 3260 -j ACCEPT; iptables -D OUTPUT -p tcp -j DROP;'
    full_cmd = f"{install_cmd} {drop_rule} {{ sleep {drop_time_in_sec}; {undrop_rule} }} > /dev/null 2> /dev/null &"

    pod_exec(pod_name, constant.LONGHORN_NAMESPACE, full_cmd)
