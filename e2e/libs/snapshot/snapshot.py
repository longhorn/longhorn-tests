from snapshot.base import Base
from snapshot.crd import CRD
from snapshot.rest import Rest

from strategy import LonghornOperationStrategy

import time

from utility.utility import filter_cr
from utility.utility import get_retry_count_and_interval
from utility.utility import logging


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

    def delete_cr(self, volume_name, snapshot_id):
        return self.snapshot.delete_cr(volume_name, snapshot_id)

    def revert(self, volume_name, snapshot_id):
        return self.snapshot.revert(volume_name, snapshot_id)

    def purge(self, volume_name, wait):
        return self.snapshot.purge(volume_name, wait)

    def wait_for_snapshot_purge_completed(self, volume_name):
        return self.snapshot.wait_for_snapshot_purge_completed(volume_name)

    def wait_for_snapshot_purge_start(self, volume_name):
        return self.snapshot.wait_for_snapshot_purge_start(volume_name)

    def is_parent_of(self, volume_name, parent_id, child_id):
        return self.snapshot.is_parent_of(volume_name, parent_id, child_id)

    def is_parent_of_volume_head(self, volume_name, parent_id):
        return self.snapshot.is_parent_of_volume_head(volume_name, parent_id)

    def is_existing(self, volume_name, snapshot_id):
        return self.snapshot.is_existing(volume_name, snapshot_id)

    def is_marked_as_removed(self, volume_name, snapshot_id):
        return self.snapshot.is_marked_as_removed(volume_name, snapshot_id)

    def is_not_marked_as_removed(self, volume_name, snapshot_id):
        return self.snapshot.is_not_marked_as_removed(volume_name, snapshot_id)

    def get_checksum(self, volume_name, snapshot_id):
        return self.snapshot.get_checksum(volume_name, snapshot_id)

    def wait_for_snapshot_checksum_to_be_created(self, volume_name, snapshot_id):
        return self.snapshot.wait_for_snapshot_checksum_to_be_created(volume_name, snapshot_id)

    def get_expansion_snapshot_name(self, volume_name):
        # The volume-expansion system snapshot CR is named
        # "expand-<size>-<volume_name>". Wait for the manager to create it,
        # then return its name.
        retry_count, retry_interval = get_retry_count_and_interval()
        for i in range(retry_count):
            snapshots = filter_cr(
                "longhorn.io", "v1beta2", "longhorn-system", "snapshots",
                label_selector=f"longhornvolume={volume_name}")
            items = snapshots.get("items", []) if snapshots else []
            for snapshot in items:
                name = snapshot["metadata"]["name"]
                if name.startswith("expand-"):
                    return name
            logging(f"Waiting for expansion snapshot CR of volume "
                    f"{volume_name} ... ({i})")
            time.sleep(retry_interval)
        assert False, \
            f"Expansion snapshot CR of volume {volume_name} not found"
