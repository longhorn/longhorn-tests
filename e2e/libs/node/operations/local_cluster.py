from node.operations.abstract_cloud_provider import AbstractCloudProvider
from node import Nodes
from utility import Utility

class LocalCluster(AbstractCloudProvider):
    def __init__(self) -> None:
        super().__init__()

    def get_all_node_instances(self):
        Nodes.refresh_node_list()
        return Nodes.all_nodes

    def get_node_instance(self, node_name):
        for instance in Nodes.all_nodes:
            if instance['name'] == node_name:
                return instance

        raise Exception(f"can not find {node_name} instance")

    # Not supported
    def power_off_node_instance(self, node_name):
        print('NotImplemented')

    # Not supported
    def power_on_node_instance(self, node_name=""):
        print('NotImplemented')
