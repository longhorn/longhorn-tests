from kubernetes import client

def get_node_by_name(node_name):
    core_api = client.CoreV1Api()
    return core_api.read_node(node_name)

def get_node_cpu_cores(node_name):
    node = get_node_by_name(node_name)
    return node.status.capacity['cpu']
