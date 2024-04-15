import os
from utility.utility import get_longhorn_client
from setting.constant import SETTING_BACKUP_TARGET
from setting.constant import SETTING_BACKUP_TARGET_CREDENTIAL_SECRET
from setting.constant import SETTING_BACKUPSTORE_POLL_INTERVAL

class Setting:

    def __init__(self):
        self.longhorn_client = get_longhorn_client()

    def get_backupstore_url(self):
        backupstore = os.environ['LONGHORN_BACKUPSTORES']
        backupstore = backupstore.replace(" ", "")
        backupstores = backupstore.split(",")
        assert len(backupstores) != 0
        return backupstores

    def get_backupstore_poll_interval(self):
        poll_interval = os.environ['LONGHORN_BACKUPSTORE_POLL_INTERVAL']
        assert len(poll_interval) != 0
        return poll_interval

    def set_backupstore(self):
        backupstores = self.get_backupstore_url()
        poll_interval = self.get_backupstore_poll_interval()
        for backupstore in backupstores:
            backupsettings = backupstore.split("$")
            self.set_backupstore_url(backupsettings[0])
            self.set_backupstore_credential_secret(backupsettings[1])
            self.set_backupstore_poll_interval(poll_interval)
            break

    def reset_backupstore_setting(self):
        backup_target_setting = self.longhorn_client.by_id_setting(SETTING_BACKUP_TARGET)
        self.longhorn_client.update(backup_target_setting, value="")

        backup_target_credential_setting = self.longhorn_client.by_id_setting(
            SETTING_BACKUP_TARGET_CREDENTIAL_SECRET)
        self.longhorn_client.update(backup_target_credential_setting, value="")

        backup_store_poll_interval = self.longhorn_client.by_id_setting(
            SETTING_BACKUPSTORE_POLL_INTERVAL)
        self.longhorn_client.update(backup_store_poll_interval, value="300")

    def set_backupstore_url(self, url):
        backup_target_setting = self.longhorn_client.by_id_setting(SETTING_BACKUP_TARGET)
        backup_target_setting = self.longhorn_client.update(backup_target_setting,
                                                            value=url)
        assert backup_target_setting.value == url

    def set_backupstore_credential_secret(self, credential_secret):
        backup_target_credential_setting = self.longhorn_client.by_id_setting(
            SETTING_BACKUP_TARGET_CREDENTIAL_SECRET)
        backup_target_credential_setting = self.longhorn_client.update(
            backup_target_credential_setting, value=credential_secret)
        assert backup_target_credential_setting.value == credential_secret

    def set_backupstore_poll_interval(self, poll_interval):
        backup_store_poll_interval_setting = self.longhorn_client.by_id_setting(
            SETTING_BACKUPSTORE_POLL_INTERVAL)
        backup_target_poll_interal_setting = self.longhorn_client.update(
            backup_store_poll_interval_setting, value=poll_interval)
        assert backup_target_poll_interal_setting.value == poll_interval

    def get_backup_target(self):
        backup_target_setting = self.longhorn_client.by_id_setting(SETTING_BACKUP_TARGET)
        return backup_target_setting.value

    def get_secret(self):
        backup_target_credential_setting = self.longhorn_client.by_id_setting(
            SETTING_BACKUP_TARGET_CREDENTIAL_SECRET)
        return backup_target_credential_setting.value
