import logging

from common_keywords import common_keywords
from replica_keywords import replica_keywords
from node import Nodes

class node_keywords:

    def __init__(self):
        self.volume = common_keywords.volume_instance
        self.replica = common_keywords.replica_instance
        self.node_operation = common_keywords.node_operation_instance
        self.node_exec = common_keywords.node_exec_instance

    def power_off_node(self, node_index):
        node_name = Nodes.get_name_by_index(int(node_index))
        logging.info(f"powering off the node {node_name}")
        self.node_operation.power_off_node_instance(node_name=node_name)

    def power_on_node(self, node_index):
        node_name = Nodes.get_name_by_index(int(node_index))
        logging.info(f"powering on the node {node_name}")
        self.node_operation.power_on_node_instance(node_name=node_name)

    def get_node_state(self, node_index):
        node_name = Nodes.get_name_by_index(int(node_index))
        logging.info(f"getting the node {node_name} state")
        return Nodes.get_node_state(node_name)

    def get_node_replica_count(self, node_index, volume_name):
        node_name = Nodes.get_name_by_index(int(node_index))
        logging.info(
            f'getting the volume {volume_name} replica count on the node {node_name}')
        response = self.replica.get_replica(volume_name, node_name)
        replicas = response['items']
        return len(replicas)

    def restore_node_state(self):
        Nodes.cleanup()

    def cleanup_resources_on_node(self):
        self.node_exec.cleanup()

    def get_cluster_node_indices(self):
        node_indices = {}

        for node in Nodes.all_nodes:
            node_name = node['name']
            nodex_index = Nodes.get_index_by_name(node_name)

            # sort according to whether the node has a replica
            replica = self.replica.get_replica(volume_name="", node_name=node_name)
            if len(replica["items"]) > 0:
                node_indices[nodex_index] = True
            else:
                node_indices[nodex_index] = False

        sorted_node_indices = dict(sorted(node_indices.items(), key=lambda item: item[1],reverse=True))

        return list(sorted_node_indices.keys())

    def get_replica_node_indices(self, volume_name):
        with_replica_nodes = []
        for node_index in self.get_cluster_node_indices():
            node_name = Nodes.all_nodes[node_index]['name']
            logging.info(f'node_name={node_name}')
            replica = self.replica.get_replica(volume_name, node_name)
            if len(replica["items"]) > 0:
                with_replica_nodes.append(Nodes.get_index_by_name(node_name))

        return with_replica_nodes