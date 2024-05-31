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

    def get_backup(self, volume_name, backup_id):
        return self.backup.get(volume_name, backup_id)

    def delete_backup_volume(self, volume_name):
        return self.backup.delete_backup_volume(volume_name)

    def cleanup_backups(self):
        if get_backupstore():
            self.backup.cleanup_system_backups()
            self.backup.cleanup_backup_volumes()
