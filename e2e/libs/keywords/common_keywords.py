from utility.utility import init_k8s_api_client
from node_exec import NodeExec
import logging

class common_keywords:

    def __init__(self):
        logging.warn("initialize common_keywords class")

    def init_k8s_api_client(self):
        init_k8s_api_client()

    def init_node_exec(self, test_name):
        namespace = test_name.lower().replace(' ', '-')[:63]
        logging.warn(f"namespace = {namespace}")
        NodeExec.get_instance().set_namespace(namespace)

    def cleanup_node_exec(self):
        logging.info('cleaning up resources')
        NodeExec.get_instance().cleanup()
