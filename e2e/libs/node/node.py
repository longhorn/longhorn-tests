from kubernetes import client

class Node:

    _instance = None

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        self.core_api = client.CoreV1Api()

    def get(self):
        obj = self.core_api.list_node()
        nodes = []
        for item in obj.items:
            if 'node-role.kubernetes.io/control-plane' not in item.metadata.labels and \
                    'node-role.kubernetes.io/master' not in item.metadata.labels:
                nodes.append(item.metadata.name)
        return sorted(nodes)

    def get_by_index(self, index):
        nodes = self.get()
        return nodes[index]
