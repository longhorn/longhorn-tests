from replica.base import Base
from replica.crd import CRD

from strategy import LonghornOperationStrategy


class Replica(Base):

    _strategy = LonghornOperationStrategy.CRD

    def __init__(self, node_exec):
        if self._strategy == LonghornOperationStrategy.CRD:
            self.replica = CRD(node_exec)

    # delete replicas, if input parameters are empty then will delete all
    def delete_replica(self, volume_name="", node_name=""):
        return self.replica.delete_replica(volume_name, node_name)

    def get_replica(self, volume_name, node_name):
        return self.replica.get_replica(volume_name, node_name)

    def wait_for_replica_rebuilding_start(self, volume_name, node_name):
        return self.replica.wait_for_replica_rebuilding_start(volume_name,node_name)

    def wait_for_replica_rebuilding_complete(self, volume_name, node_name):
        return self.replica.wait_for_replica_rebuilding_complete(volume_name,node_name)
