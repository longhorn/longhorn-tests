import time

from node_exec import NodeExec

from strategy import LonghornOperationStrategy

from volume.base import Base
from volume.crd import CRD
from volume.rest import Rest


class Volume(Base):

    _strategy = LonghornOperationStrategy.CRD

    def __init__(self):
        node_exec = NodeExec.get_instance()
        if self._strategy == LonghornOperationStrategy.CRD:
            self.volume = CRD(node_exec)
        else:
            self.volume = Rest(node_exec)

    def get(self, volume_name):
        return self.volume.get(volume_name)

    def create(self, volume_name, size, replica_count):
        return self.volume.create(volume_name, size, replica_count)

    def attach(self, volume_name, node_name):
        return self.volume.attach(volume_name, node_name)

    def detach(self, volume_name):
        return self.volume.detach(volume_name)

    def delete(self, volume_name):
        return self.volume.delete(volume_name)

    def wait_for_volume_state(self, volume_name, desired_state):
        return self.volume.wait_for_volume_state(volume_name, desired_state)

    def wait_for_volume_attached(self, volume_name):
        self.volume.wait_for_volume_state(volume_name, "attached")
        self.volume.wait_for_volume_robustness_not(volume_name, "unknown")

    def wait_for_volume_detached(self, volume_name):
        self.volume.wait_for_volume_state(volume_name, "detached")

    def wait_for_volume_healthy(self, volume_name):
        self.volume.wait_for_volume_state(volume_name, "attached")
        self.volume.wait_for_volume_robustness(volume_name, "healthy")

    def wait_for_volume_expand_to_size(self, volume_name, size):
        return self.volume.wait_for_volume_expand_to_size(volume_name, size)

    def get_endpoint(self, volume_name):
        return self.volume.get_endpoint(volume_name)

    def write_random_data(self, volume_name, size):
        return self.volume.write_random_data(volume_name, size)

    def keep_writing_data(self, volume_name):
        return self.volume.keep_writing_data(volume_name, 256)

    def delete_replica(self, volume_name, node_name):
        return self.volume.delete_replica(volume_name, node_name)

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

    def check_data_checksum(self, volume_name, checksum):
        return self.volume.check_data_checksum(volume_name, checksum)

    def cleanup(self, volume_names):
        return self.volume.cleanup(volume_names)
