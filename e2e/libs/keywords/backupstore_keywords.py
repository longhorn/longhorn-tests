from backupstore import Nfs, S3

import os

from utility.utility import get_backupstore


class backupstore_keywords:

    def __init__(self):
        backupstore = get_backupstore()
        if backupstore.startswith("s3"):
            self.backupstore = S3()
        elif backupstore.startswith("nfs"):
            self.backupstore = Nfs()

    def create_dummy_in_progress_backup(self, volume_name):

        dummy_backup_cfg_data = {"Name": "dummy_backup",
                                 "VolumeName": volume_name,
                                 "CreatedTime": ""}

        self.backupstore.write_backup_cfg_file(volume_name,
                                               "backup-dummy",
                                               dummy_backup_cfg_data)

    def delete_dummy_in_progress_backup(self, volume_name):
        self.backupstore.delete_backup_cfg_file(volume_name,
                                                "backup-dummy")

    def corrupt_backup_cfg_file(self, volume_name, backup_name):

        corrupt_backup_cfg_data = "{corrupt: definitely"

        self.backupstore.write_backup_cfg_file(volume_name,
                                               backup_name,
                                               corrupt_backup_cfg_data)

    def create_file_in_backups_folder(self, volume_name, file_name):
        prefix = self.backupstore.get_backup_volume_prefix(volume_name)
        file_path = os.path.join(prefix, "backups" ,file_name)
        self.backupstore.create_file_in_backupstore(file_path)

    def delete_file_in_backups_folder(self, volume_name, file_name):
        prefix = self.backupstore.get_backup_volume_prefix(volume_name)
        file_path = os.path.join(prefix, "backups" ,file_name)
        self.backupstore.delete_file_in_backupstore(file_path)

    def create_dummy_backup_from_file(self, file_name):
        self.backupstore.create_dummy_backup(file_name)

    def set_backupstore_poll_interval(self, poll_interval):
        self.backupstore.set_backupstore_poll_interval(poll_interval)
