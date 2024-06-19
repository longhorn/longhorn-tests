from backup.base import Base
from backup.crd import CRD
from backup.rest import Rest
from strategy import LonghornOperationStrategy
from utility.utility import logging


class Backup(Base):

    _strategy = LonghornOperationStrategy.REST

    def __init__(self):
        if self._strategy == LonghornOperationStrategy.CRD:
            self.backup = CRD()
        else:
            self.backup = Rest()

    def create(self, volume_name, backup_id):
        return self.backup.create(volume_name, backup_id)

    def get(self, backup_id, volume_name):
        return self.backup.get(backup_id, volume_name)

    def get_backup_volume(self, volume_name):
        return self.backup.get_backup_volume(volume_name)

    def list(self, volume_name):
        return self.backup.list(volume_name)

    def verify_no_error(self, volume_name):
        backup_volume = self.get_backup_volume(volume_name)
        assert not backup_volume['messages'], \
            f"expect backup volume {volume_name} has no error, but it's {backup_volume['messages']}"

    def delete(self, volume_name, backup_id):
        return NotImplemented

    def delete_backup_volume(self, volume_name):
        return self.backup.delete_backup_volume(volume_name)

    def restore(self, volume_name, backup_id):
        return NotImplemented

    def check_restored_volume_checksum(self, volume_name, backup_name):
        return self.backup.check_restored_volume_checksum(volume_name, backup_name)

    def cleanup_backup_volumes(self):
        return self.backup.cleanup_backup_volumes()

    def cleanup_system_backups(self):
        return self.backup.cleanup_system_backups()
