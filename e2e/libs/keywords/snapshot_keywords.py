from snapshot import Snapshot


class snapshot_keywords:

    def __init__(self):
        self.snapshot = Snapshot()

    def create_snapshot(self, volume_name, snapshot_id, waiting=True):
        self.snapshot.create(volume_name, snapshot_id, waiting)

    def delete_snapshot(self, volume_name, snapshot_id):
        self.snapshot.delete(volume_name, snapshot_id)

    def delete_snapshot_cr(self, volume_name, snapshot_id):
        self.snapshot.delete_cr(volume_name, snapshot_id)

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

    def get_checksum(self, volume_name, snapshot_id):
        return self.snapshot.get_checksum(volume_name, snapshot_id)

    def wait_for_snapshot_checksum_to_be_created(self, volume_name, snapshot_id):
        return self.snapshot.wait_for_snapshot_checksum_to_be_created(volume_name, snapshot_id)

    def get_snapshot_by_name(self, volume_name, snapshot_name):
        return self.snapshot.get_snapshot_by_name(volume_name, snapshot_name)

    def wait_for_snapshot_to_be_created(self, volume_name, snapshot_name):
        return self.snapshot.wait_for_snapshot_to_be_created(volume_name, snapshot_name)

    def wait_for_snapshot_to_be_deleted(self, volume_name, snapshot_name):
        return self.snapshot.wait_for_snapshot_to_be_deleted(volume_name, snapshot_name)
