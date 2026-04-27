import asyncio
import os
import time

from node import Node
from node_exec import NodeExec
from node_exec.constant import HOST_ROOTFS

from utility.constant import LABEL_TEST
from utility.constant import LABEL_TEST_VALUE
import utility.constant as constant
from utility.utility import pod_exec
from utility.utility import logging

from workload.pod import create_pod
from workload.pod import delete_pod
from workload.pod import new_pod_manifest
from workload.pod import wait_for_pod_status
from workload.constant import IMAGE_BUSYBOX, IMAGE_NETWORK_TEST


def setup_control_plane_network_latency(latency_in_ms=0):
    if latency_in_ms != 0:
        logging(f"Setting up control plane network latency with {latency_in_ms} ms")
        control_plane_nodes = Node().list_node_names_by_role("control-plane")
        for control_plane_node in control_plane_nodes:
            ns_mnt = os.path.join(HOST_ROOTFS, "proc/1/ns/mnt")
            ns_net = os.path.join(HOST_ROOTFS, "proc/1/ns/net")
            manifest = new_pod_manifest(
                image=IMAGE_BUSYBOX,
                command=["nsenter", f"--mount={ns_mnt}", f"--net={ns_net}", "--", "sh"],
                args=["-c", f"INTERFACE=$(ip route show default | awk '/default/ {{print $5}}') && tc qdisc replace dev $INTERFACE root netem delay {latency_in_ms}ms"],
                node_name=control_plane_node,
                labels = {LABEL_TEST: LABEL_TEST_VALUE}
            )
            pod_name = manifest['metadata']['name']
            create_pod(manifest, is_wait_for_pod_succeeded=True)


def cleanup_control_plane_network_latency():
    logging("Cleaning up control plane network latency")
    control_plane_nodes = Node().list_node_names_by_role("control-plane")
    for control_plane_node in control_plane_nodes:
        ns_mnt = os.path.join(HOST_ROOTFS, "proc/1/ns/mnt")
        ns_net = os.path.join(HOST_ROOTFS, "proc/1/ns/net")
        manifest = new_pod_manifest(
            image=IMAGE_BUSYBOX,
            command=["nsenter", f"--mount={ns_mnt}", f"--net={ns_net}", "--", "sh"],
            args=["-c", f"INTERFACE=$(ip route show default | awk '/default/ {{print $5}}') && tc qdisc del dev $INTERFACE root || true"],
            node_name=control_plane_node,
            labels = {LABEL_TEST: LABEL_TEST_VALUE}
        )
        pod_name = manifest['metadata']['name']
        create_pod(manifest, is_wait_for_pod_succeeded=True)


def disconnect_node_network(node_name, disconnection_time_in_sec=10, port_number=None, wait=True):
    if port_number:
        logging(f"Disconnecting node {node_name} network for {disconnection_time_in_sec} seconds on port {port_number}")
        args = ["-c", f"iptables -I INPUT -p tcp --dport {port_number} -j DROP && iptables -I INPUT -p tcp --sport {port_number} -j DROP && iptables -I OUTPUT -p tcp --dport {port_number} -j DROP && iptables -I OUTPUT -p tcp --sport {port_number} -j DROP && sleep {disconnection_time_in_sec} && iptables -D INPUT -p tcp --dport {port_number} -j DROP && iptables -D INPUT -p tcp --sport {port_number} -j DROP && iptables -D OUTPUT -p tcp --dport {port_number} -j DROP && iptables -D OUTPUT -p tcp --sport {port_number} -j DROP"]
    else:
        logging(f"Disconnecting node {node_name} network for {disconnection_time_in_sec} seconds")
        args = ["-c", f"INTERFACE=$(ip route show default | awk '/default/ {{print $5}}') && tc qdisc replace dev $INTERFACE root netem loss 100% && sleep {disconnection_time_in_sec} && tc qdisc del dev $INTERFACE root || true"]

    ns_mnt = os.path.join(HOST_ROOTFS, "proc/1/ns/mnt")
    ns_net = os.path.join(HOST_ROOTFS, "proc/1/ns/net")
    manifest = new_pod_manifest(
        image=IMAGE_NETWORK_TEST,
        command=["nsenter", f"--mount={ns_mnt}", f"--net={ns_net}", "--", "sh"],
        args=args,
        node_name=node_name,
        labels={LABEL_TEST: LABEL_TEST_VALUE}
    )
    pod_name = manifest['metadata']['name']
    create_pod(manifest, is_wait_for_pod_succeeded=wait)
    return pod_name


# For now, drop_pod_egress_traffic only works in "suse-like" container images. It relies on iptables userspace 
# utilities, which must generally be installed before execution.
def drop_pod_egress_traffic(pod_name, drop_time_in_sec=10):
    logging(f"Dropping pod {pod_name} egress traffic for {drop_time_in_sec} seconds")
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

def disconnect_pod_network(pod_name, disconnection_time_in_sec=10, port_number=None, wait=True):
    if port_number:
        logging(f"Disconnecting pod {pod_name} network for {disconnection_time_in_sec} seconds on port {port_number}")
        cmd = f"zypper install -y iptables && iptables -I INPUT -p tcp --dport {port_number} -j DROP && iptables -I INPUT -p tcp --sport {port_number} -j DROP && iptables -I OUTPUT -p tcp --dport {port_number} -j DROP && iptables -I OUTPUT -p tcp --sport {port_number} -j DROP && sleep {disconnection_time_in_sec} && iptables -D INPUT -p tcp --dport {port_number} -j DROP && iptables -D INPUT -p tcp --sport {port_number} -j DROP && iptables -D OUTPUT -p tcp --dport {port_number} -j DROP && iptables -D OUTPUT -p tcp --sport {port_number} -j DROP > /dev/null 2> /dev/null &"
    else:
        logging(f"Disconnecting pod {pod_name} network for {disconnection_time_in_sec} seconds")
        cmd = f"zypper install -y iptables && iptables -I INPUT -j DROP && iptables -I OUTPUT -j DROP && sleep {disconnection_time_in_sec} && iptables -D INPUT -j DROP && iptables -D OUTPUT -j DROP > /dev/null 2> /dev/null &"

    wait_for_pod_status(pod_name, "Running", namespace=constant.LONGHORN_NAMESPACE)
    pod_exec(pod_name, constant.LONGHORN_NAMESPACE, cmd)
    if wait:
        time.sleep(disconnection_time_in_sec)
