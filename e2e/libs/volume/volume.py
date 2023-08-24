import logging

from volume.base import Base
from volume.crd import CRD
from volume.rest import Rest
from strategy import LonghornOperationStrategy


class Volume(Base):

    _strategy = LonghornOperationStrategy.CRD

    def __init__(self, node_exec):
        if self._strategy == LonghornOperationStrategy.CRD:
            self.volume = CRD(node_exec)
        else:
            self.volume = Rest(node_exec)

    def create(self, volume_name, size, replica_count, volume_type):
        return self.volume.create(volume_name, size, replica_count, volume_type)

    def create_with_manifest(self, manifest):
        return self.volume.create_with_manifest(manifest)

    def get(self, volume_name):
        return self.volume.get(volume_name)

    def delete(self, volume_name=""):
        return self.volume.delete(volume_name)

    def attach(self, volume_name, node_name):
        return self.volume.attach(volume_name, node_name)

    def wait_for_volume_state(self, volume_name, desired_state):
        return self.volume.wait_for_volume_state(volume_name, desired_state)

    def get_volume_state(self, volume_name):
        return self.volume.get_volume_state(volume_name)

    def get_endpoint(self, volume_name):
        return self.volume.get_endpoint(volume_name)

    def write_random_data(self, volume_name, size):
        return self.volume.write_random_data(volume_name, size)

    def check_data(self, volume_name, checksum):
        return self.volume.check_data(volume_name, checksum)

    def delete_and_wait_pod(self, volume_name):
        self.volume.delete_and_wait_pod(volume_name)
