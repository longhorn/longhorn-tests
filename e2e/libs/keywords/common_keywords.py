from node import Node
from utility.utility import init_k8s_api_client
from utility.utility import generate_name_with_suffix


class common_keywords:

    def __init__(self):
        pass

    def init_k8s_api_client(self):
        init_k8s_api_client()

    def generate_name_with_suffix(self, kind, suffix):
        return generate_name_with_suffix(kind, suffix)

    def get_worker_nodes(self):
        return Node().list_node_names_by_role("worker")

    def get_node_by_index(self, node_id):
        return Node().get_node_by_index(node_id)
