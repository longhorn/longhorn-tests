from snapshot.base import Base
from utility.utility import logging
from utility.utility import get_longhorn_client
from utility.utility import get_retry_count_and_interval
from utility.utility import get_cr
import utility.constant as constant
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
            snapshots = self.list(volume_name)
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
        logging(f"Created volume {volume_name} snapshot {snapshot_id} {snap_name}")

        return snapshot

    def create_periodically(self, volume_name, interval, duration):
        """Create a snapshot every `interval` seconds for `duration` seconds.

        Return the names of the snapshots that became ready to use.

        Each snapshot is recorded as soon as it becomes ready, so it is
        still returned if Longhorn deletes it later. After the last
        snapshot is created, wait up to 60 seconds for the remaining ones
        to become ready. A snapshot that cannot be created is logged and
        skipped.
        """
        pending = {}
        ready = []

        def collect_ready():
            for snap_name in list(pending):
                cr = self.get_snapshot_cr(snap_name)
                if cr is None:
                    logging(f"Volume {volume_name} snapshot {snap_name} CR is gone before it was seen ready")
                    del pending[snap_name]
                elif cr.get("status", {}).get("readyToUse"):
                    logging(f"Volume {volume_name} snapshot {snap_name} created at {pending[snap_name]:.1f}s is ready")
                    ready.append(snap_name)
                    del pending[snap_name]

        start = time.time()
        while (elapsed := time.time() - start) < duration:
            try:
                snap_name = self.volume.get(volume_name).snapshotCRCreate().name
                pending[snap_name] = elapsed
                logging(f"Created volume {volume_name} snapshot {snap_name} at {elapsed:.1f}s")
            except Exception as e:
                logging(f"Failed to create volume {volume_name} snapshot at {elapsed:.1f}s: {e}")
            collect_ready()
            time.sleep(max(0, interval - (time.time() - start - elapsed)))

        deadline = time.time() + 60
        collect_ready()
        while pending and time.time() < deadline:
            time.sleep(self.retry_interval)
            collect_ready()
        if pending:
            logging(f"Volume {volume_name} snapshots {list(pending)} did not become ready")
        return ready

    def get_snapshot_cr(self, snapshot_name):
        return get_cr(
            group="longhorn.io",
            version="v1beta2",
            namespace=constant.LONGHORN_NAMESPACE,
            plural="snapshots",
            name=snapshot_name,
            wait=False
        )

    def get(self, volume_name, snapshot_id):
        snapshots = self.list(volume_name)
        for snapshot in snapshots:
            if snapshot.name != "volume-head" and str(self.get_snapshot_id(snapshot.name)) == str(snapshot_id):
                return snapshot
        return None

    def get_volume_head(self, volume_name):
        snapshots = self.list(volume_name)
        for snapshot in snapshots:
            if snapshot.name == "volume-head":
                return snapshot
        assert False

    def get_snapshot_by_name(self, volume_name, snapshot_name):
        snapshots = self.list(volume_name)
        for snapshot in snapshots:
            if snapshot.name == snapshot_name:
                logging(f"Got snapshot {snapshot_name} of volume {volume_name}")
                return snapshot
        return None

    def wait_for_snapshot_to_be_created(self, volume_name, snapshot_name):
        for i in range(self.retry_count):
            logging(f"Trying to get volume {volume_name} snapshot {snapshot_name} ... ({i})")
            try:
                snapshot = self.get_snapshot_by_name(volume_name, snapshot_name)
                if snapshot:
                    return snapshot
            except Exception as e:
                logging(f"Failed to get volume {volume_name} snapshot {snapshot_name}: {e}")
            time.sleep(self.retry_interval)
        assert False, f"Failed to get volume {volume_name} snapshot {snapshot_name}"

    def wait_for_snapshot_to_be_deleted(self, volume_name, snapshot_name):
        for i in range(self.retry_count):
            logging(f"Waiting for volume {volume_name} snapshot {snapshot_name} to be deleted ... ({i})")
            try:
                snapshot = self.get_snapshot_by_name(volume_name, snapshot_name)
                if not snapshot or snapshot.removed:
                    return
            except Exception as e:
                logging(f"Failed to wait for volume {volume_name} snapshot {snapshot_name} to be deleted: {e}")
            time.sleep(self.retry_interval)
        assert False, f"Failed to wait for volume {volume_name} snapshot {snapshot_name} to be deleted"

    def list(self, volume_name):
        for i in range(self.retry_count):
            try:
                return self.volume.get(volume_name).snapshotList().data
            except Exception as e:
                logging(f"Failed to list volume {volume_name} snapshots: {e}")
            time.sleep(self.retry_interval)
        assert False, f"Failed to list volume {volume_name} snapshots"

    def delete(self, volume_name, snapshot_id):
        logging(f"Deleting volume {volume_name} snapshot {snapshot_id}")
        snapshot = self.get(volume_name, snapshot_id)
        self.volume.get(volume_name).snapshotDelete(name=snapshot.name)

    def delete_by_name(self, volume_name, snapshot_name):
        logging(f"Deleting volume {volume_name} snapshot {snapshot_name}")
        self.volume.get(volume_name).snapshotDelete(name=snapshot_name)

    def delete_cr(self, volume_name, snapshot_id):
        logging(f"Deleting volume {volume_name} snapshot {snapshot_id} CR")
        snapshot = self.get(volume_name, snapshot_id)
        self.volume.get(volume_name).snapshotCRDelete(name=snapshot.name)

    def revert(self, volume_name, snapshot_id):
        logging(f"Reverting volume {volume_name} to snapshot {snapshot_id}")
        snapshot = self.get(volume_name, snapshot_id)
        self.volume.get(volume_name).snapshotRevert(name=snapshot.name)

    def purge(self, volume_name, wait):
        logging(f"Purging volume {volume_name} snapshot")

        volume = self.volume.get(volume_name)
        volume.snapshotPurge()

        if not wait:
            return

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

    def is_snapshot_purging(self, volume_name):
        volume = self.volume.get(volume_name)
        purge_status = volume.purgeStatus
        for status in purge_status:
            if status.isPurging:
                return True
        return False

    def wait_for_snapshot_purge_completed(self, volume_name):
        for i in range(self.retry_count):
            logging(f"Waiting for volume {volume_name} snapshot purge completed ... ({i})")
            if not self.is_snapshot_purging(volume_name):
                return
            time.sleep(self.retry_interval)
        assert False, f"Failed to wait for {volume_name} snapshot purge completed"

    def wait_for_snapshot_purge_start(self, volume_name):
        for i in range(self.retry_count):
            logging(f"Waiting for volume {volume_name} snapshot purge start ... ({i})")
            if self.is_snapshot_purging(volume_name):
                return
            time.sleep(self.retry_interval)
        assert False, f"Failed to wait for {volume_name} snapshot purge start"

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

    def is_not_marked_as_removed(self, volume_name, snapshot_id):
        snapshot = self.get(volume_name, snapshot_id)
        assert not snapshot.removed

    def get_checksum(self, volume_name, snapshot_id):
        snapshot = self.get(volume_name, snapshot_id)
        return snapshot.checksum

    def wait_for_snapshot_checksum_to_be_created(self, volume_name, snapshot_id):
        for i in range(self.retry_count):
            logging(f"Trying to get volume {volume_name} snapshot {snapshot_id} checksum ... ({i})")
            try:
                checksum = self.get_checksum(volume_name, snapshot_id)
                if checksum:
                    logging(f"Got volume {volume_name} snapshot {snapshot_id} checksum: {checksum}")
                    return checksum
            except Exception as e:
                logging(f"Failed to get volume {volume_name} snapshot {snapshot_id} checksum: {e}")
            time.sleep(self.retry_interval)
        assert False, f"Failed to get volume {volume_name} snapshot {snapshot_id} checksum"