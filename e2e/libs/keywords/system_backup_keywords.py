from system_backup import SystemBackup


class system_backup_keywords:

    def __init__(self):
        self.system_backup = SystemBackup()

    def create_system_backup(self, backup_name):
        self.system_backup.create(backup_name)

    def create_system_restore(self, backup_name):
        self.system_backup.restore(backup_name)

    def cleanup_system_backups(self):
        self.system_backup.cleanup_system_backups()

    def cleanup_system_restores(self):
        self.system_backup.cleanup_system_restores()
