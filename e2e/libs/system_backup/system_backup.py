from system_backup.base import Base
from system_backup.crd import CRD
from system_backup.rest import Rest
from strategy import LonghornOperationStrategy

class SystemBackup(Base):

    _strategy = LonghornOperationStrategy.REST

    def __init__(self):
        if self._strategy == LonghornOperationStrategy.CRD:
            self.system_backup = CRD()
        else:
            self.system_backup = Rest()

    def create(self, backup_name):
        return self.system_backup.create(backup_name)

    def restore(self, backup_name):
        return self.system_backup.restore(backup_name)

    def cleanup_system_backups(self):
        return self.system_backup.cleanup_system_backups()

    def cleanup_system_restores(self):
        return self.system_backup.cleanup_system_restores()
