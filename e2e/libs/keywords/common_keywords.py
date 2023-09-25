from utility.utility import init_k8s_api_client
from node_exec import NodeExec

class common_keywords:

    def __init__(self):
        pass

    def init_k8s_api_client(self):
        init_k8s_api_client()

    def init_node_exec(self, test_name):
        namespace = test_name.lower().replace(' ', '-')[:63]
        NodeExec.get_instance().set_namespace(namespace)

    def cleanup_node_exec(self):
        NodeExec.get_instance().cleanup()
