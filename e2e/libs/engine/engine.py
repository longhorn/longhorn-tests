from engine.base import Base
from engine.crd import CRD
from strategy import LonghornOperationStrategy


class Engine(Base):

    _strategy = LonghornOperationStrategy.CRD

    def __init__(self):
        if self._strategy == LonghornOperationStrategy.CRD:
            self.engine = CRD()

    def get_engine(self, volume_name, node_name):
        return self.engine.get_engine(volume_name, node_name)

    # delete engines, if input parameters are empty then will delete all
    def delete_engine(self, volume_name="", node_name=""):
        return self.engine.delete_engine(volume_name, node_name)
