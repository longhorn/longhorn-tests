import time

from persistentvolumeclaim import PersistentVolumeClaim

from replica import Replica

from utility.constant import LABEL_TEST
from utility.constant import LABEL_TEST_VALUE
from utility.utility import get_retry_count_and_interval
from utility.utility import logging

from volume import Volume

from workload.statefulset import create_statefulset
from workload.statefulset import delete_statefulset
from workload.statefulset import get_statefulset
from workload.statefulset import list_statefulsets
from workload.statefulset import scale_statefulset
from workload.statefulset import wait_for_statefulset_replicas_ready
from workload.workload import get_workload_persistent_volume_claim_names
from workload.workload import get_workload_volume_name


class statefulset_keywords:

    def __init__(self):
        self.persistentvolumeclaim = PersistentVolumeClaim()
        self.replica = Replica()
        self.volume = Volume()

    def cleanup_statefulsets(self):
        statefulsets = list_statefulsets(label_selector=f"{LABEL_TEST}={LABEL_TEST_VALUE}")

        logging(f'Cleaning up {len(statefulsets.items)} statefulsets')
        for statefulset in statefulsets.items:
            self.delete_statefulset(statefulset.metadata.name)

    def create_statefulset(self, name, volume_type="RWO", sc_name="longhorn", size=None, node_name=None, spread=None):
        logging(f'Creating {volume_type} statefulset {name} with {sc_name} storageclass and size = {size}, node_name = {node_name}, spread = {spread}')
        create_statefulset(name, volume_type, sc_name, size, node_name, spread)

    def get_statefulset_pod_volume_name(self, statefulset_name, ordinal):
        claim_name = f"pod-data-{statefulset_name}-{ordinal}"
        self.persistentvolumeclaim.wait_for_pvc_phase(claim_name, "Bound")
        return self.persistentvolumeclaim.get_volume_name(claim_name)

    def get_statefulset_volume_replica_nodes(self, statefulset_name):
        replica_nodes = {}
        for claim_name in get_workload_persistent_volume_claim_names(statefulset_name):
            volume_name = self.persistentvolumeclaim.get(claim_name).spec.volume_name
            if volume_name:
                replica_nodes[volume_name] = [r['spec']['nodeID'] for r in self.replica.get(volume_name, None)]
        return replica_nodes

    def wait_for_statefulset_volume_replicas_on_nodes(self, statefulset_name, node_count):
        logging(f'Waiting for the volume replicas of statefulset {statefulset_name} to be on {node_count} different nodes')
        retry_count, retry_interval = get_retry_count_and_interval()
        nodes = []
        for i in range(retry_count):
            nodes = sum(self.get_statefulset_volume_replica_nodes(statefulset_name).values(), [])
            if nodes and all(nodes) and len(set(nodes)) == int(node_count):
                return
            time.sleep(retry_interval)
        assert False, f"Expected the volume replicas of statefulset {statefulset_name} on {node_count} different nodes, got {nodes}"

    def wait_for_statefulset_volume_replicas_off_node(self, statefulset_name, node_name):
        logging(f'Waiting for the volume replicas of statefulset {statefulset_name} to leave node {node_name}')
        retry_count, retry_interval = get_retry_count_and_interval()
        replica_nodes = {}
        for i in range(retry_count):
            replica_nodes = self.get_statefulset_volume_replica_nodes(statefulset_name)
            # An evicted replica stays until its replacement is rebuilt.
            if replica_nodes and all(len(nodes) == 1 and nodes[0] and nodes[0] != node_name for nodes in replica_nodes.values()):
                return
            time.sleep(retry_interval)
        assert False, f"Expected one replica off node {node_name} for each volume of statefulset {statefulset_name}, got {replica_nodes}"

    def get_statefulset_volume_on_node(self, statefulset_name, node_name):
        for volume_name, nodes in self.get_statefulset_volume_replica_nodes(statefulset_name).items():
            if node_name in nodes:
                return volume_name
        assert False, f"No volume of statefulset {statefulset_name} has a replica on node {node_name}"

    def wait_for_statefulset_volumes_detached(self, statefulset_name):
        for volume_name in self.get_statefulset_volume_replica_nodes(statefulset_name):
            logging(f'Waiting for volume {volume_name} of statefulset {statefulset_name} to be detached')
            self.volume.wait_for_volume_detached(volume_name)

    def delete_statefulset(self, name):
        logging(f'Deleting statefulset {name}')
        delete_statefulset(name)

    def get_statefulset(self, statefulset_name):
        return get_statefulset(statefulset_name)

    def scale_statefulset(self, statefulset_name, replica_count):
        logging(f'Scaling statefulset {statefulset_name} to {replica_count}')
        return scale_statefulset(statefulset_name, replica_count)

    def scale_statefulset_down(self, statefulset_name):
        logging(f'Scaling statefulset {statefulset_name} down')
        scale_statefulset(statefulset_name, 0)

        volume_name = get_workload_volume_name(statefulset_name)
        self.volume.wait_for_volume_detached(volume_name)

    def scale_statefulset_up(self, statefulset_name, replicaset_count=3):
        logging(f'Scaling statefulset {statefulset_name} up to {replicaset_count}')
        scale_statefulset(statefulset_name, replicaset_count)

        volume_name = get_workload_volume_name(statefulset_name)
        self.volume.wait_for_volume_healthy(volume_name)

        self.wait_for_statefulset_replicas_ready(statefulset_name, replicaset_count)

    def wait_for_statefulset_replicas_ready(self, statefulset_name, expected_ready_count):
        logging(f'Waiting for statefulset {statefulset_name} to have {expected_ready_count} replicas ready')
        wait_for_statefulset_replicas_ready(statefulset_name, int(expected_ready_count))
