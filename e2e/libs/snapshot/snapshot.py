from snapshot.base import Base
from snapshot.crd import CRD
from snapshot.rest import Rest

from strategy import LonghornOperationStrategy


class Snapshot(Base):

    _strategy = LonghornOperationStrategy.REST

    def __init__(self):
        if self._strategy == LonghornOperationStrategy.CRD:
            self.snapshot = CRD()
        else:
            self.snapshot = Rest()

    def create(self, volume_name, snapshot_id, waiting=True):
        return self.snapshot.create(volume_name, snapshot_id, waiting)

    def get(self, volume_name, snapshot_id):
        return self.snapshot.get(volume_name, snapshot_id)

    def get_snapshot_by_name(self, volume_name, snapshot_name):
        return self.snapshot.get_snapshot_by_name(volume_name, snapshot_name)

    def wait_for_snapshot_to_be_created(self, volume_name, snapshot_name):
        return self.snapshot.wait_for_snapshot_to_be_created(volume_name, snapshot_name)

    def wait_for_snapshot_to_be_deleted(self, volume_name, snapshot_name):
        return self.snapshot.wait_for_snapshot_to_be_deleted(volume_name, snapshot_name)

    def get_volume_head(self, volume_name):
        return self.snapshot.get_volume_head(volume_name)

    def list(self, volume_name):
        return self.snapshot.list(volume_name)

    def delete(self, volume_name, snapshot_id):
        return self.snapshot.delete(volume_name, snapshot_id)

    def revert(self, volume_name, snapshot_id):
        return self.snapshot.revert(volume_name, snapshot_id)

    def purge(self, volume_name):
        return self.snapshot.purge(volume_name)

    def is_parent_of(self, volume_name, parent_id, child_id):
        return self.snapshot.is_parent_of(volume_name, parent_id, child_id)

    def is_parent_of_volume_head(self, volume_name, parent_id):
        return self.snapshot.is_parent_of_volume_head(volume_name, parent_id)

    def is_existing(self, volume_name, snapshot_id):
        return self.snapshot.is_existing(volume_name, snapshot_id)

    def is_marked_as_removed(self, volume_name, snapshot_id):
        return self.snapshot.is_marked_as_removed(volume_name, snapshot_id)

    def get_checksum(self, volume_name, snapshot_id):
        return self.snapshot.get_checksum(volume_name, snapshot_id)
