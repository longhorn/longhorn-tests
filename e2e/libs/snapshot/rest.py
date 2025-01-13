from snapshot.base import Base
from utility.utility import logging
from utility.utility import get_longhorn_client
from utility.utility import get_retry_count_and_interval
from node_exec import NodeExec
from volume import Rest as RestVolume
import time


class Rest(Base):

    def __init__(self):
        self.volume = RestVolume()
        self.retry_count, self.retry_interval = get_retry_count_and_interval()

    def create(self, volume_name, snapshot_id, waiting):
        logging(f"Creating volume {volume_name} snapshot {snapshot_id}")
        volume = self.volume.get(volume_name)
        snapshot = volume.snapshotCRCreate()
        snap_name = snapshot.name

        if not waiting:
            return snapshot

        snapshot_created = False
        for i in range(self.retry_count):
            snapshots = volume.snapshotList().data
            for vs in snapshots:
                if vs.name == snap_name:
                    snapshot_created = True
                    snapshot = vs 
                    break
            if snapshot_created is True:
                break
            time.sleep(self.retry_interval)

        assert snapshot_created

        self.set_snapshot_id(snap_name, snapshot_id)

        return snapshot

    def get(self, volume_name, snapshot_id):
        snapshots = self.list(volume_name)
        for snapshot in snapshots:
            if snapshot.name != "volume-head" and self.get_snapshot_id(snapshot.name) == snapshot_id:
                return snapshot
        return None

    def get_volume_head(self, volume_name):
        snapshots = self.list(volume_name)
        for snapshot in snapshots:
            if snapshot.name == "volume-head":
                return snapshot
        assert False

    def list(self, volume_name):
        return self.volume.get(volume_name).snapshotList().data

    def delete(self, volume_name, snapshot_id):
        logging(f"Deleting volume {volume_name} snapshot {snapshot_id}")
        snapshot = self.get(volume_name, snapshot_id)
        self.volume.get(volume_name).snapshotDelete(name=snapshot.name)

    def revert(self, volume_name, snapshot_id):
        logging(f"Reverting volume {volume_name} to snapshot {snapshot_id}")
        snapshot = self.get(volume_name, snapshot_id)
        self.volume.get(volume_name).snapshotRevert(name=snapshot.name)

    def purge(self, volume_name):
        logging(f"Purging volume {volume_name} snapshot")

        volume = self.volume.get(volume_name)
        volume.snapshotPurge()

        completed = 0
        last_purge_progress = {}
        purge_status = {}
        for i in range(self.retry_count):
            completed = 0
            volume = self.volume.get(volume_name)
            purge_status = volume.purgeStatus
            for status in purge_status:
                assert status.error == "", f"Expect purge without error, but its' {status.error}"

                progress = status.progress
                assert progress <= 100, f"Expect purge progress <= 100, but it's {status}"
                replica = status.replica
                last = last_purge_progress.get(replica)
                assert last is None or last <= status.progress, f"Expect purge progress increasing, but it didn't: current status = {status}, last progress = {last_purge_progress}"
                last_purge_progress["replica"] = progress

                if status.state == "complete":
                    assert progress == 100
                    completed += 1
            if completed == len(purge_status):
                break
            time.sleep(self.retry_interval)
        assert completed == len(purge_status)

    def is_parent_of(self, volume_name, parent_id, child_id):
        logging(f"Checking volume {volume_name} snapshot {parent_id} is parent of snapshot {child_id}")
        parent = self.get(volume_name, parent_id)
        child = self.get(volume_name, child_id)
        if child.name not in parent.children.keys() or child.parent != parent.name:
            logging(f"Expect snapshot {parent_id} is parent of snapshot {child_id}, but it's not")
            time.sleep(self.retry_count)

    def is_parent_of_volume_head(self, volume_name, parent_id):
        parent = self.get(volume_name, parent_id)
        volume_head = self.get_volume_head(volume_name)
        if volume_head.name not in parent.children.keys() or volume_head.parent != parent.name:
            logging(f"Expect snapshot {parent_id} is parent of volume-head, but it's not")
            time.sleep(self.retry_count)

    def is_existing(self, volume_name, snapshot_id):
        return self.get(volume_name, snapshot_id)

    def is_marked_as_removed(self, volume_name, snapshot_id):
        snapshot = self.get(volume_name, snapshot_id)
        assert snapshot.removed
