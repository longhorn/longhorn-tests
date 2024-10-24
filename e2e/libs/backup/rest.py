from backup.base import Base
from utility.utility import logging
from utility.utility import get_longhorn_client
from utility.utility import get_retry_count_and_interval
from utility.utility import get_all_crs
from volume import Rest as RestVolume
from snapshot import Snapshot as RestSnapshot
import time


class Rest(Base):

    def __init__(self):
        self.volume = RestVolume()
        self.snapshot = RestSnapshot()
        self.retry_count, self.retry_interval = get_retry_count_and_interval()

    def create(self, volume_name, backup_id):
        # create snapshot
        snapshot = self.snapshot.create(volume_name, backup_id)

        volume = self.volume.get(volume_name)
        volume.snapshotBackup(name=snapshot.name)
        # after backup request we need to wait for completion of the backup
        # since the backup.cfg will only be available once the backup operation
        # has been completed
        self.wait_for_backup_completed(volume_name, snapshot.name)

        backup = self.get_by_snapshot(volume_name, snapshot.name)

        for i in range(self.retry_count):
            logging(f"Waiting for volume {volume_name} lastBackup updated ... ({i})")
            volume = self.volume.get(volume_name)
            if volume.lastBackup == backup.name:
                break
            time.sleep(self.retry_interval)
        assert volume.lastBackup == backup.name, \
            f"expect volume lastBackup is {backup.name}, but it's {volume.lastBackup}"
        assert volume.lastBackupAt != "", \
            f"expect volume lastBackupAt is not empty, but it's {volume.lastBackupAt}"

        self.set_backup_id(backup.name, backup_id)
        self.set_data_checksum(backup.name, self.volume.get_last_data_checksum(volume_name))

        return backup

    def get(self, backup_id, volume_name):
        backups = self.list(volume_name)
        for backup in backups:
            if self.get_backup_id(backup.name) == backup_id:
                return backup
        return None

    def get_from_list(self, backup_list, backup_id):
        for backup in backup_list["items"]:
            try:
                if backup['metadata']['annotations']['test.longhorn.io/backup-id'] == backup_id:
                    return backup
            except KeyError as e:
                logging(f"Missing key in backup metadata: {str(e)} for backup {backup['metadata']['name']}")
            except Exception as e:
                logging(f"Unexpected error accessing backup {backup['metadata']['name']}: {str(e)}")
        return None

    def get_by_snapshot(self, volume_name, snapshot_name):
        """
        look for a backup from snapshot on the backupstore
        it's important to note that this can only be used for a completed backup
        since the backup.cfg will only be written once a backup operation has
        been completed successfully
        """
        for i in range(self.retry_count):
            logging(f"Trying to get backup from volume {volume_name} snapshot {snapshot_name} ... ({i})")
            try:
                backup_volume = self.get_backup_volume(volume_name)
                backups = backup_volume.backupList().data
                for backup in backups:
                    if backup.snapshotName == snapshot_name:
                        return backup
            except Exception as e:
                logging(f"Failed to find backup from volume {volume_name} snapshot {snapshot_name} with error: {e}")
            time.sleep(self.retry_interval)
        assert False, f"Failed to find backup from volume {volume_name} snapshot {snapshot_name}"

    def get_backup_volume(self, volume_name):
        logging(f"Trying to get backup volume {volume_name} ...")
        backup_volumes = get_longhorn_client().list_backupVolume().data
        for backup_volume in backup_volumes:
            if backup_volume.name == volume_name and backup_volume.created != "":
                return backup_volume
        return None

    def wait_for_backup_completed(self, volume_name, snapshot_name):
        completed = False
        for i in range(self.retry_count):
            logging(f"Waiting for backup from volume {volume_name} snapshot {snapshot_name} completed ... ({i})")
            volume = self.volume.get(volume_name)
            for backup in volume.backupStatus:
                if backup.snapshot != snapshot_name:
                    continue
                elif backup.state == "Completed":
                    assert backup.progress == 100 and backup.error == "", f"backup = {backup}"
                    completed = True
                    break
            if completed:
                break
            time.sleep(self.retry_interval)
        assert completed, f"Expected from volume {volume_name} snapshot {snapshot_name} completed, but it's {volume}"

    def list(self, volume_name):
        if not volume_name:
            backup_list = []
            vol_list = self.volume.list()
            for volume_name in vol_list:
                backup_volume = self.get_backup_volume(volume_name)
                if backup_volume:
                    backup_list.extend(backup_volume.backupList().data)
            return backup_list
        else:
            backup_volume = self.get_backup_volume(volume_name)
            return backup_volume.backupList().data

    def list_all(self):
        return get_all_crs(group="longhorn.io",
                      version="v1beta2",
                      namespace="longhorn-system",
                      plural="backups",
                      )

    def assert_all_backups_before_uninstall_exist(self, backups_before_uninstall):
        for i in range(self.retry_count):
            time.sleep(self.retry_interval)
            try:
                current_backups = self.list_all()
                assert len(current_backups["items"]) == len(backups_before_uninstall["items"])
                break
            except Exception as e:
                logging(f"{e}")
                continue

        target_backup_names = {(item["metadata"]["name"]) for item in backups_before_uninstall["items"]}
        for item in current_backups["items"]:
            backup_name = item["metadata"]["name"]
            assert backup_name in target_backup_names, f"Error: Backup {backup_name} not found in {target_backup_names}"

            for i in range(self.retry_count):
                time.sleep(self.retry_interval)
                volume_name = item["status"]["volumeName"]
                if self.get_backup_volume(volume_name) != None:
                    break

    def delete(self, volume_name, backup_id):
        return NotImplemented

    def delete_backup_volume(self, volume_name):
        bv = get_longhorn_client().by_id_backupVolume(volume_name)
        get_longhorn_client().delete(bv)
        self.wait_for_backup_volume_delete(volume_name)

    def wait_for_backup_volume_delete(self, name):
        retry_count, retry_interval = get_retry_count_and_interval()
        for _ in range(retry_count):
            bvs = get_longhorn_client().list_backupVolume()
            found = False
            for bv in bvs:
                if bv.name == name:
                    found = True
                    break
            if not found:
                break
            time.sleep(retry_interval)
        assert not found

    def restore(self, volume_name, backup_id):
        return NotImplemented

    def check_restored_volume_checksum(self, volume_name, backup_name):
        expected_checksum = self.get_data_checksum(backup_name)
        actual_checksum = self.volume.get_checksum(volume_name)
        logging(f"Checked volume {volume_name}. Expected checksum = {expected_checksum}. Actual checksum = {actual_checksum}")
        assert actual_checksum == expected_checksum

    def get_restored_checksum(self, backup_name):
        expected_checksum = self.get_data_checksum(backup_name)
        logging(f"Expected checksum = {expected_checksum}")
        return expected_checksum

    def cleanup_backup_volumes(self):
        backup_volumes = get_longhorn_client().list_backup_volume()

        # we delete the whole backup volume, which skips block gc
        for backup_volume in backup_volumes:
            self.delete_backup_volume(backup_volume.name)

        backup_volumes = get_longhorn_client().list_backup_volume()
        assert backup_volumes.data == []

    def cleanup_system_backups(self):

        system_backups = get_longhorn_client().list_system_backup()
        for system_backup in system_backups:
            # ignore the error when clean up
            try:
                get_longhorn_client().delete(system_backup)
            except Exception as e:
                name = system_backup['name']
                print("\nException when cleanup system backup ", name)
                print(e)

        ok = False
        retry_count, retry_interval = get_retry_count_and_interval()
        for _ in range(retry_count):
            system_backups = get_longhorn_client().list_system_backup()
            if len(system_backups) == 0:
                ok = True
                break
            time.sleep(retry_interval)
        assert ok
