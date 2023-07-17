import logging

from volume.abstract_volume import AbstractVolume
from volume.crd_volume import CRDVolume
from volume.rest_volume import RestVolume
from strategy import LonghornOperationStrategy


class Volume(AbstractVolume):

    _strategy = LonghornOperationStrategy.CRD

    def __init__(self, node_exec):
        if self._strategy == LonghornOperationStrategy.CRD:
            self.volume = CRDVolume(node_exec)
        else:
            self.volume = RESTVolume(node_exec)

    def get(self, volume_name):
        return self.volume.get(volume_name)

    def delete_volume(self, volume_name=""):
        return self.volume.delete(volume_name)

    def create(self, volume_name, size, replica_count, volume_type):
        return self.volume.create(volume_name, size, replica_count, volume_type)

    def attach(self, volume_name, node_name):
        return self.volume.attach(volume_name, node_name)

    def wait_for_volume_state(self, volume_name, desired_state):
        return self.volume.wait_for_volume_state(volume_name, desired_state)

    def get_volume_state(self, volume_name):
        volume = self.get(volume_name)
        return self.volume.get_volume_state(volume_name)

    def get_endpoint(self, volume_name):
        return self.volume.get_endpoint(volume_name)

    def write_random_data(self, volume_name, size):
        return self.volume.write_random_data(volume_name, size)

    def write_random_data_v2(self, volume_name, size):
        return self.volume.write_random_data_v2(volume_name, size)

    # delete replicas, if input parameters are empty then will delete all
    def delete_replica(self, volume_name="", node_name=""):
        return self.volume.delete_replica(volume_name, node_name)

    def get_replica(self, volume_name, node_name):
        return self.volume.get_replica(volume_name, node_name)

    def get_engine(self, volume_name, node_name):
        return self.volume.get_engine(volume_name, node_name)

    # delete engines, if input parameters are empty then will delete all
    def delete_engine(self, volume_name="", node_name=""):
        return self.volume.delete_engine(volume_name, node_name)

    def wait_for_replica_rebuilding_start(self, volume_name, node_name):
        return self.volume.wait_for_replica_rebuilding_start(
            volume_name,
            node_name
        )

    def wait_for_replica_rebuilding_complete(self, volume_name, node_name):
        return self.volume.wait_for_replica_rebuilding_complete(
            volume_name,
            node_name
        )

    def check_data(self, volume_name, checksum):
        return self.volume.check_data(volume_name, checksum)

    def clean_up(self):
        logging.info("cleaning volume related resources")
        # Replicas
        self.delete_replica()
        # Engines
        self.delete_engine()
        # Volumes
        self.delete_volume()

