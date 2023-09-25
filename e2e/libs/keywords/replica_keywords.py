from utility.utility import logging
from node import Nodes
from common_keywords import common_keywords

class replica_keywords:

    def __init__(self):
        self.replica = common_keywords.replica_instance
        self.volume = common_keywords.volume_instance

    def delete_replica(self, volume_name, node_index):
        node_name = Nodes.get_name_by_index(int(node_index))
        logging(f"Deleting volume {volume_name}'s replica on the node {node_name}")
        self.replica.delete_replica(volume_name, node_name)

    def wait_for_replica_rebuilding_start(self, volume_name, node_index):
        node_name = Nodes.get_name_by_index(int(node_index))
        logging(f"Waiting volume {volume_name}'s replica on node {node_name} rebuilding start")
        self.replica.wait_for_replica_rebuilding_start(volume_name, node_name)

    def wait_for_replica_rebuilding_complete(self, volume_name, node_index):
        node_name = Nodes.get_name_by_index(int(node_index))
        logging(f"Waiting volume {volume_name}'s replica on node {node_name} rebuilding complete")
        self.replica.wait_for_replica_rebuilding_complete(
            volume_name, node_name)

    #TODO
    # keywords layer can only call lower implementation layer to complete its work
    # and should not have any business logic here

    def get_replica_state(self, volume_name, node_index):
        node_name = Nodes.get_name_by_index(int(node_index))
        logging(f"Getting volume {volume_name}'s replica on the node {node_name} state")

        resp = self.replica.get_replica(volume_name, node_name)
        assert resp != "", f"failed to get the volume {volume_name} replicas"

        replicas = resp["items"]
        if len(replicas) == 0:
            return

        replicas_states = {}
        for replica in replicas:
            replica_name = replica["metadata"]["name"]
            replica_state = replica['status']['currentState']
            replicas_states[replica_name] = replica_state
        return replicas_states

    def wait_for_replica_created(self, volume_name, expected_replica_count):
        # wait for a period of time for the replica to be created
        current_replica_count = 0
        count = 1
        while expected_replica_count != current_replica_count and count <= 180:
            replicas = self.replica.get_replica(volume_name, "")
            current_replica_count = len(replicas)
            count += 1
        assert expected_replica_count != current_replica_count, f'replica creation is not ready: {current_replica_count}'
