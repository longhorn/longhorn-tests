from snapshot import Snapshot
from utility.utility import logging


class snapshot_keywords:

    def __init__(self):
        self.snapshot = Snapshot()

    def create_snapshot(self, volume_name, snapshot_id):
        self.snapshot.create(volume_name, snapshot_id)

    def delete_snapshot(self, volume_name, snapshot_id):
        self.snapshot.delete(volume_name, snapshot_id)

    def revert_snapshot(self, volume_name, snapshot_id):
        self.snapshot.revert(volume_name, snapshot_id)

    def purge_snapshot(self, volume_name):
        self.snapshot.purge(volume_name)

    def is_parent_of(self, volume_name, parent_id, child_id):
        self.snapshot.is_parent_of(volume_name, parent_id, child_id)

    def is_parent_of_volume_head(self, volume_name, parent_id):
        self.snapshot.is_parent_of_volume_head(volume_name, parent_id)

    def is_marked_as_removed(self, volume_name, snapshot_id):
        self.snapshot.is_marked_as_removed(volume_name, snapshot_id)

    def is_not_existing(self, volume_name, snapshot_id):
        assert not self.snapshot.is_existing(volume_name, snapshot_id)

    def is_existing(self, volume_name, snapshot_id):
        assert self.snapshot.is_existing(volume_name, snapshot_id)
