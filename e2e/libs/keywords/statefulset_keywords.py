from persistentvolumeclaim import PersistentVolumeClaim

from utility.constant import LABEL_TEST
from utility.constant import LABEL_TEST_VALUE
from utility.utility import logging

from volume import Volume

from workload.statefulset import create_statefulset
from workload.statefulset import delete_statefulset
from workload.statefulset import get_statefulset
from workload.statefulset import list_statefulsets
from workload.statefulset import scale_statefulset
from workload.statefulset import wait_for_statefulset_replicas_ready
from workload.workload import get_workload_volume_name



class statefulset_keywords:

    def __init__(self):
        self.persistentvolumeclaim = PersistentVolumeClaim()
        self.volume = Volume()

    def cleanup_statefulsets(self):
        statefulsets = list_statefulsets(label_selector=f"{LABEL_TEST}={LABEL_TEST_VALUE}")

        logging(f'Cleaning up {len(statefulsets.items)} statefulsets')
        for statefulset in statefulsets.items:
            self.delete_statefulset(statefulset.metadata.name)

    def create_statefulset(self, name, volume_type="RWO", sc_name="longhorn"):
        logging(f'Creating {volume_type} statefulset {name} with {sc_name} storageclass')
        create_statefulset(name, volume_type, sc_name)

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
        wait_for_statefulset_replicas_ready(statefulset_name, expected_ready_count)
