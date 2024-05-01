import os
import time
from utility.utility import logging
from utility.utility import get_longhorn_client
from utility.utility import get_retry_count_and_interval

class Setting:

    SETTING_BACKUP_TARGET = "backup-target"
    SETTING_BACKUP_TARGET_CREDENTIAL_SECRET = "backup-target-credential-secret"
    SETTING_BACKUPSTORE_POLL_INTERVAL = "backupstore-poll-interval"

    def __init__(self):
        self.longhorn_client = get_longhorn_client()
        self.retry_count, self.retry_interval = get_retry_count_and_interval()

    def update_setting(self, key, value):
        for i in range(self.retry_count):
            try:
                logging(f"Trying to update setting {key} to {value} ... ({i})")
                setting = self.longhorn_client.by_id_setting(key)
                self.longhorn_client.update(setting, value=value)
                break
            except Exception as e:
                logging(e)
            time.sleep(self.retry_interval)

    def get_setting(self, key):
        return self.longhorn_client.by_id_setting(key).value

    def get_backupstore_url(self):
        return os.environ.get('LONGHORN_BACKUPSTORE')

    def get_backupstore_poll_interval(self):
        return os.environ.get('LONGHORN_BACKUPSTORE_POLL_INTERVAL')

    def set_backupstore(self):
        backupstore = self.get_backupstore_url()
        if backupstore:
            backupsettings = backupstore.split("$")
            self.update_setting(self.SETTING_BACKUP_TARGET, backupsettings[0])
            if len(backupsettings) > 1:
                self.update_setting(self.SETTING_BACKUP_TARGET_CREDENTIAL_SECRET, backupsettings[1])

            poll_interval = self.get_backupstore_poll_interval()
            self.update_setting(self.SETTING_BACKUPSTORE_POLL_INTERVAL, poll_interval)

    def reset_backupstore(self):
        self.update_setting(self.SETTING_BACKUP_TARGET, "")
        self.update_setting(self.SETTING_BACKUP_TARGET_CREDENTIAL_SECRET, "")
        self.update_setting(self.SETTING_BACKUPSTORE_POLL_INTERVAL, "300")

    def get_backup_target(self):
        return self.get_setting(self.SETTING_BACKUP_TARGET)

    def get_secret(self):
        return self.get_setting(self.SETTING_BACKUP_TARGET_CREDENTIAL_SECRET)
