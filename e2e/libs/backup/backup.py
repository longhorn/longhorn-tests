import time
from backup.base import Base
from backup.crd import CRD
from backup.rest import Rest
from utility.utility import logging
from utility.utility import get_retry_count_and_interval
from strategy import LonghornOperationStrategy


class Backup(Base):

    _strategy = LonghornOperationStrategy.REST

    def __init__(self):
        self.retry_count, self.retry_interval = get_retry_count_and_interval()
        if self._strategy == LonghornOperationStrategy.CRD:
            self.backup = CRD()
        else:
            self.backup = Rest()

    def create(self, volume_name, backup_id, wait, snapshot_id=None):
        return self.backup.create(volume_name, backup_id, wait, snapshot_id)

    def get(self, backup_id, volume_name):
        return self.backup.get(backup_id, volume_name)

    def get_backup_url(self, backup_id, volume_name):
        for i in range(self.retry_count):
            logging(f"Getting volume {volume_name} backup {backup_id} url ... ({i})")
            backup = self.get(backup_id, volume_name)
            if backup and backup.url:
                logging(f"Got volume {volume_name} backup {backup_id} url={backup.url}")
                return backup.url
            time.sleep(self.retry_interval)
        assert False, f"Failed to get volume {volume_name} backup {backup_id} url: {backup}"

    def get_latest_backup_url(self, volume_name):
        latest_backup = self.backup.get_latest(volume_name)
        return latest_backup.url

    def get_from_list(self, backup_list, backup_id):
        return self.backup.get_from_list(backup_list, backup_id)

    def get_backup_volume(self, volume_name):
        return self.backup.get_backup_volume(volume_name)

    def list(self, volume_name):
        return self.backup.list(volume_name)

    def list_all(self):
        return self.backup.list_all()

    def assert_all_backups_before_uninstall_exist(self, backups_before_uninstall):
        return self.backup.assert_all_backups_before_uninstall_exist(backups_before_uninstall)

    def verify_no_error(self, volume_name):
        backup_volume = self.get_backup_volume(volume_name)
        assert not backup_volume['messages'], \
            f"expect backup volume {volume_name} has no error, but it's {backup_volume['messages']}"

    def verify_errors(self, volume_name):
        for i in range(self.retry_count):
            logging(f"Waiting for volume {volume_name} error backups ... ({i})")
            backups = self.backup.list_all()["items"]
            for backup in backups:
                if backup["metadata"]["labels"]["backup-volume"] == volume_name and backup["status"]["state"] == "Error":
                    logging(f"Got error backup {backup}")
                    return
            time.sleep(self.retry_interval)
        assert False, f"Failed to get volume {volume_name} error backup: {backups}"

    def verify_backup_count(self, volume_name, expected_backup_count):
        volume_backup_count= len(self.list(volume_name))
        assert volume_backup_count == expected_backup_count, \
            f"Expected {expected_backup_count} backups, but found {volume_backup_count} backups for volume {volume_name}"

    def wait_for_snapshot_backup_to_be_created(self, volume_name, snapshot_name):
        return self.backup.wait_for_snapshot_backup_to_be_created(volume_name, snapshot_name)

    def wait_for_snapshot_backup_to_be_deleted(self, volume_name, snapshot_name):
        return self.backup.wait_for_snapshot_backup_to_be_deleted(volume_name, snapshot_name)

    def wait_for_backup_ready(self, backup_name):
        for i in range(self.retry_count):
            logging(f"Waiting for backup {backup_name} ready ... ({i})")
            backup = self.backup.get_by_name(backup_name)
            if backup and backup['status']['state'] == "Completed":
                return
            time.sleep(self.retry_interval)
        assert False, f"Failed to wait for backup {backup_name} ready"

    def delete(self, volume_name, backup_id):
        return NotImplemented

    def delete_backup_volume(self, volume_name):
        return self.backup.delete_backup_volume(volume_name)

    def restore(self, volume_name, backup_id):
        return NotImplemented

    def check_restored_volume_checksum(self, volume_name, backup_name):
        return self.backup.check_restored_volume_checksum(volume_name, backup_name)

    def get_restored_checksum(self, backup_name):
        return self.backup.get_restored_checksum(backup_name)

    def cleanup_backup_volumes(self):
        return self.backup.cleanup_backup_volumes()

    def cleanup_backups(self):
        return self.backup.cleanup_backups()

    def check_snapshot_exists_for_backup(self, volume_name, backup_id, exists=True):
        backup = self.backup.get(backup_id, volume_name)
        if not backup or not backup.snapshotName:
            raise ValueError(f"Backup {backup_id} not found or missing snapshot name")

        snap_name = backup.snapshotName
        snapshot_id = self.backup.snapshot.get_snapshot_id(snap_name)
        snap = self.backup.snapshot.get(volume_name, snapshot_id)
        snap_exists = not snap.removed
        assert snap_exists == exists, f"Snapshot {snap_name} exists: {snap_exists}, expected: {exists}"
