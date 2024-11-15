from backup import Backup

from utility.utility import logging
from utility.utility import get_backupstore


class backup_keywords:

    def __init__(self):
        self.backup = Backup()

    def create_backup(self, volume_name, backup_id):
        self.backup.create(volume_name, backup_id)

    def verify_no_error(self, volume_name):
        self.backup.verify_no_error(volume_name)

    def verify_backup_count(self, volume_name, expected_backup_count):
        self.backup.verify_backup_count(volume_name, expected_backup_count)

    def get_backup_name(self, backup_id, volume_name=None):
        return self.backup.get(backup_id, volume_name).name

    def get_backup_url(self, backup_id, volume_name=None):
        return self.backup.get(backup_id, volume_name).url

    def get_backup_url_from_backup_list(self, backup_list, backup_id):
        backup = self.backup.get_from_list(backup_list, backup_id)
        return backup["status"]["url"]

    def get_backup_data_from_backup_list(self, backup_list, backup_id):
        backup = self.backup.get_from_list(backup_list, backup_id)
        return backup['metadata']['annotations']["test.longhorn.io/data-checksum"]

    def get_backup_name_from_backup_list(self, backup_list, backup_id):
        backup = self.backup.get_from_list(backup_list, backup_id)
        return backup['metadata']['name']

    def delete_backup_volume(self, volume_name):
        return self.backup.delete_backup_volume(volume_name)

    def check_restored_volume_checksum(self, volume_name, backup_name):
        logging(f"Checking restored volume {volume_name} data is backup {backup_name}")
        self.backup.check_restored_volume_checksum(volume_name, backup_name)

    def get_restored_checksum(self, backup_name):
        return self.backup.get_restored_checksum(backup_name)

    def cleanup_backups(self):
        if get_backupstore():
            self.backup.cleanup_system_backups()
            self.backup.cleanup_backup_volumes()

    def list_all_backups(self):
        all_backups = self.backup.list_all()
        return all_backups

    def assert_all_backups_before_uninstall_exist(self, backups_before_uninstall):
        self.backup.assert_all_backups_before_uninstall_exist(backups_before_uninstall)
