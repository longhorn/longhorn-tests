from robot.libraries.BuiltIn import BuiltIn

from utility.utility import get_control_plane_nodes

from node_exec import NodeExec


def get_control_plane_node_network_latency_in_ms():
    latency_in_ms = int(BuiltIn().get_variable_value("${CONTROL_PLANE_NODE_NETWORK_LATENCY_IN_MS}", default="0"))
    return latency_in_ms

def setup_control_plane_network_latency():
    latency_in_ms = get_control_plane_node_network_latency_in_ms()
    if latency_in_ms != 0:
        nodes = get_control_plane_nodes()
        for node in nodes:
            cmd = f"tc qdisc replace dev eth0 root netem delay {latency_in_ms}ms"
            res = NodeExec.get_instance().issue_cmd(node, cmd)
            cmd = f"tc qdisc show dev eth0 | grep delay"
            res = NodeExec.get_instance().issue_cmd(node, cmd)
            assert res, "setup control plane network latency failed"

def cleanup_control_plane_network_latency():
    latency_in_ms = get_control_plane_node_network_latency_in_ms()
    if latency_in_ms != 0:
        nodes = get_control_plane_nodes()
        for node in nodes:
            cmd = "tc qdisc del dev eth0 root"
            res = NodeExec.get_instance().issue_cmd(node, cmd)
            cmd = f"tc qdisc show dev eth0 | grep -v delay"
            res = NodeExec.get_instance().issue_cmd(node, cmd)
            assert res, "cleanup control plane network failed"