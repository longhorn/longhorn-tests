from strategy import LonghornOperationStrategy

from sharemanager.base import Base
from sharemanager.crd import CRD
from sharemanager.rest import Rest


class ShareManager(Base):

    _strategy = LonghornOperationStrategy.CRD

    def __init__(self):
        if self._strategy == LonghornOperationStrategy.CRD:
            self.sharemanager = CRD()
        else:
            self.sharemanager = Rest()

    def list(self):
        return self.sharemanager.list()

    def delete(self, name):
        return self.sharemanager.delete(name)

    def wait_for_running(self, name):
        return self.sharemanager.wait_for_running(name)

    def get(self, name):
        return self.sharemanager.get(name)

    def wait_for_restart(self, name, last_creation_time):
        return self.sharemanager.wait_for_restart(name, last_creation_time)
