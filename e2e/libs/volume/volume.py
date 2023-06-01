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
            self.volume = REST(node_exec)

    def get(self, volume_name):
        return self.volume.get(volume_name)

    def create(self, volume_name, size, replica_count):
        return self.volume.create(volume_name, size, replica_count)

    def attach(self, volume_name, node_name):
        return self.volume.attach(volume_name, node_name)

    def wait_for_volume_state(self, volume_name, desired_state):
        return self.volume.wait_for_volume_state(volume_name, desired_state)

    def get_endpoint(self, volume_name):
        return self.volume.get_endpoint(volume_name)

    def write_random_data(self, volume_name, size):
        return self.volume.write_random_data(volume_name, size)

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

    def check_data(self, volume_name, checksum):
        return self.volume.check_data(volume_name, checksum)
