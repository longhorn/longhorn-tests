from kubernetes import client

def get_node_by_name(node_name):
    core_api = client.CoreV1Api()
    return core_api.read_node(node_name)

def get_node_cpu_cores(node_name):
    node = get_node_by_name(node_name)
    return node.status.capacity['cpu']

def list_node_names_by_role(role="all"):
    if role not in ["all", "control-plane", "worker"]:
        raise ValueError("Role must be one of 'all', 'master' or 'worker'")

    def filter_nodes(nodes, condition):
        return [node.metadata.name for node in nodes if condition(node)]

    core_api = client.CoreV1Api()
    nodes = core_api.list_node().items

    control_plane_labels = ['node-role.kubernetes.io/master', 'node-role.kubernetes.io/control-plane']

    if role == "all":
        return sorted(filter_nodes(nodes, lambda node: True))

    if role == "control-plane":
        condition = lambda node: all(label in node.metadata.labels for label in control_plane_labels)
        return sorted(filter_nodes(nodes, condition))

    if role == "worker":
        condition = lambda node: not any(label in node.metadata.labels for label in control_plane_labels)
        return sorted(filter_nodes(nodes, condition))
