from replica.base import Base
from replica.crd import CRD

from strategy import LonghornOperationStrategy


class Replica(Base):

    _strategy = LonghornOperationStrategy.CRD

    def __init__(self):
        if self._strategy == LonghornOperationStrategy.CRD:
            self.replica = CRD()

    # delete replicas, if input parameters are empty then will delete all
    def delete(self, volume_name="", node_name=""):
        return self.replica.delete(volume_name, node_name)

    def get(self, volume_name, node_name, disk_uuid=None):
        return self.replica.get(volume_name, node_name, disk_uuid)

    def wait_for_rebuilding_start(self, volume_name, node_name):
        return self.replica.wait_for_rebuilding_start(volume_name,node_name)

    def wait_for_rebuilding_complete(self, volume_name, node_name):
        return self.replica.wait_for_rebuilding_complete(volume_name,node_name)

    def validate_replica_setting(self, volume_name, setting_name, value):
        return self.replica.validate_replica_setting(volume_name, setting_name, value)
