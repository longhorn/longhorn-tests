import asyncio
import os
import time
import shlex

from kubernetes import client
from kubernetes.client.rest import ApiException

from node import Node
from node_exec import NodeExec
from node_exec.constant import HOST_ROOTFS

from utility.constant import LABEL_TEST
from utility.constant import LABEL_TEST_VALUE
import utility.constant as constant
from utility.utility import pod_exec
from utility.utility import logging
from utility.utility import get_longhorn_namespace

from workload.pod import create_pod
from workload.pod import delete_pod
from workload.pod import new_pod_manifest
from workload.pod import wait_for_pod_status
from workload.constant import IMAGE_BUSYBOX, IMAGE_NETWORK_TEST


GLOBAL_MANAGER_API_PARTITION_POLICY = "global-manager-api-partition"
GLOBAL_MANAGER_API_PARTITION_LABEL = "test.longhorn.io/api-partition"


def partition_global_manager_api(pod_name):
    """Block the leader's egress and remove its existing API connection."""
    namespace = get_longhorn_namespace()
    api = client.CoreV1Api()
    pod = api.read_namespaced_pod(pod_name, namespace)
    node_name = pod.spec.node_name
    pod_ip = pod.status.pod_ip
    assert pod_ip and node_name, f"Leader pod {pod_name} must be scheduled with an IP"
    service = api.read_namespaced_service("kubernetes", "default")
    api_ip = service.spec.cluster_ip
    assert api_ip and api_ip != "None", "Kubernetes API Service must have a ClusterIP"

    logging(f"Partitioning global manager {pod_name} on {node_name} "
            f"from API Service {api_ip}")
    labels = {GLOBAL_MANAGER_API_PARTITION_LABEL: "true"}
    api.patch_namespaced_pod(pod_name, namespace, {"metadata": {"labels": labels}})
    client.NetworkingV1Api().create_namespaced_network_policy(namespace, {
        "apiVersion": "networking.k8s.io/v1",
        "kind": "NetworkPolicy",
        "metadata": {
            "name": GLOBAL_MANAGER_API_PARTITION_POLICY,
            "namespace": namespace,
        },
        "spec": {
            "podSelector": {"matchLabels": labels},
            "policyTypes": ["Egress"],
            "egress": [],
        },
    })
    # NetworkPolicy may leave the existing client-go connection established.
    _delete_api_conntrack(node_name, pod_ip, api_ip)


def _delete_api_conntrack(node_name, pod_ip, api_ip):
    """Delete the pod's API Service connection using the host conntrack table."""
    # Enter only the host network namespace so conntrack and its libraries
    # come from the network helper image, not the node filesystem.
    # conntrack returns 1 when no entries match; other failures must surface.
    command = (
        f"conntrack -D -p tcp -s {shlex.quote(pod_ip)} "
        f"-d {shlex.quote(api_ip)} --dport 443 2>&1; "
        "partition_conntrack_status=$?; echo conntrack-status=$partition_conntrack_status")
    ns_net = os.path.join(HOST_ROOTFS, "proc/1/ns/net")
    output = NodeExec(node_name).issue_cmd(
        ["nsenter", f"--net={ns_net}", "--", "sh", "-c", command],
        image_name=IMAGE_NETWORK_TEST)
    status_lines = output.splitlines()
    deleted = "conntrack-status=0" in status_lines
    no_entries = ("conntrack-status=1" in status_lines and
                  "0 flow entries have been deleted" in output)
    assert deleted or no_entries, f"Failed to delete API conntrack on node {node_name}: {output}"


def cleanup_global_manager_api_partition():
    namespace = get_longhorn_namespace()
    try:
        try:
            client.NetworkingV1Api().delete_namespaced_network_policy(
                GLOBAL_MANAGER_API_PARTITION_POLICY, namespace)
        except ApiException as exc:
            if exc.status != 404:
                raise
    finally:
        api = client.CoreV1Api()
        pods = api.list_namespaced_pod(
            namespace, label_selector=f"{GLOBAL_MANAGER_API_PARTITION_LABEL}=true").items
        for pod in pods:
            try:
                api.patch_namespaced_pod(pod.metadata.name, namespace, {
                    "metadata": {"labels": {GLOBAL_MANAGER_API_PARTITION_LABEL: None}}})
            except ApiException as exc:
                if exc.status != 404:
                    raise


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


def limit_pod_traffic_to_ip(pod_name, target_ip, excluded_source_port,
                            rate_in_mbit):
    wait_for_pod_status(
        pod_name, "Running", namespace=constant.LONGHORN_NAMESPACE)

    interface = pod_exec(
        pod_name,
        constant.LONGHORN_NAMESPACE,
        f"ip route get {target_ip} | awk '{{for (i = 1; i <= NF; i++) "
        f"if ($i == \"dev\") {{print $(i + 1); exit}}}}'",
    ).strip()
    assert interface, f"Failed to find route from {pod_name} to {target_ip}"

    logging(
        f"Limiting traffic from pod {pod_name} to {target_ip} to "
        f"{rate_in_mbit} Mbit, excluding source port {excluded_source_port}"
    )
    # Classify the sync-agent server traffic first so only rebuild data is
    # rate-limited. All unrelated traffic uses the unshaped default class.
    cmd = (
        "set -eu; "
        "zypper install -y iptables > /dev/null; "
        f"tc qdisc add dev {interface} root handle 1: htb default 20; "
        f"tc class add dev {interface} parent 1: classid 1:1 "
        "htb rate 10000mbit; "
        f"tc class add dev {interface} parent 1:1 classid 1:10 "
        f"htb rate {rate_in_mbit}mbit; "
        f"tc class add dev {interface} parent 1:1 classid 1:20 "
        "htb rate 10000mbit; "
        f"tc filter add dev {interface} protocol ip parent 1: prio 1 u32 "
        "match ip protocol 6 0xff "
        f"match ip sport {excluded_source_port} 0xffff flowid 1:20; "
        f"tc filter add dev {interface} protocol ip parent 1: prio 2 u32 "
        f"match ip dst {target_ip}/32 flowid 1:10"
    )

    try:
        pod_exec(pod_name, constant.LONGHORN_NAMESPACE, cmd)
    except Exception:
        remove_pod_traffic_limit(pod_name, interface)
        raise

    return interface


def remove_pod_traffic_limit(pod_name, interface):
    logging(
        f"Removing traffic limit from pod {pod_name} interface {interface}")
    pod_exec(
        pod_name,
        constant.LONGHORN_NAMESPACE,
        f"tc qdisc del dev {interface} root handle 1: 2>/dev/null || true",
    )


def get_pod_tcp_connections(pod_name):
    output = pod_exec(
        pod_name,
        constant.LONGHORN_NAMESPACE,
        "ss -Htn state established",
    )

    connections = []
    for line in output.splitlines():
        fields = line.split()
        if len(fields) < 4:
            continue
        local_ip, local_port = _split_tcp_endpoint(fields[2])
        remote_ip, remote_port = _split_tcp_endpoint(fields[3])
        connections.append({
            "local_ip": local_ip,
            "local_port": local_port,
            "remote_ip": remote_ip,
            "remote_port": remote_port,
        })
    return connections


def drop_tcp_connection_replies(pod_name, connection,
                                drop_time_in_sec):
    rule = (
        f"-p tcp -s {connection['remote_ip']} "
        f"--sport {connection['remote_port']} "
        f"-d {connection['local_ip']} --dport {connection['local_port']} "
        "-j DROP"
    )
    logging(
        "Dropping replies to TCP connection "
        f"{connection['remote_ip']}:{connection['remote_port']} -> "
        f"{connection['local_ip']}:{connection['local_port']} for "
        f"{drop_time_in_sec} seconds"
    )
    cmd = (
        f"iptables -w -I INPUT 1 {rule}; "
        f"{{ sleep {drop_time_in_sec}; "
        f"iptables -w -D INPUT {rule} || true; }} > /dev/null 2>&1 &"
    )
    pod_exec(pod_name, constant.LONGHORN_NAMESPACE, cmd)


def _split_tcp_endpoint(endpoint):
    if endpoint.startswith("["):
        ip, port = endpoint[1:].rsplit("]:", 1)
    else:
        ip, port = endpoint.rsplit(":", 1)
    if ip.startswith("::ffff:"):
        ip = ip[len("::ffff:"):]
    return ip, int(port)
