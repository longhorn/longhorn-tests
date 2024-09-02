import os
import time

from utility.utility import get_longhorn_client
from utility.utility import get_retry_count_and_interval
from utility.utility import logging

class Setting:

    SETTING_BACKUP_TARGET = "backup-target"
    SETTING_BACKUP_TARGET_CREDENTIAL_SECRET = "backup-target-credential-secret"
    SETTING_BACKUPSTORE_POLL_INTERVAL = "backupstore-poll-interval"

    def __init__(self):
        self.retry_count, self.retry_interval = get_retry_count_and_interval()

    def update_setting(self, key, value, retry=True):
        if retry:
            for i in range(self.retry_count):
                try:
                    logging(f"Trying to update setting {key} to {value} ... ({i})")
                    setting = get_longhorn_client().by_id_setting(key)
                    get_longhorn_client().update(setting, value=value)
                    break
                except Exception as e:
                    logging(e)
                time.sleep(self.retry_interval)
        else:
            logging(f"Trying to update setting {key} to {value} ...")
            setting = get_longhorn_client().by_id_setting(key)
            get_longhorn_client().update(setting, value=value)

    def get_setting(self, key):
        return get_longhorn_client().by_id_setting(key).value

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

    def reset_settings(self):
        client = get_longhorn_client()
        for setting in client.list_setting():
            setting_name = setting.name
            setting_default_value = setting.definition.default
            setting_readonly = setting.definition.readOnly

            # We don't provide the setup for the storage network, hence there is no
            # default value. We need to skip here to avoid test failure when
            # resetting this to an empty default value.
            if setting_name == "storage-network":
                continue
            # The test CI deploys Longhorn with the setting value longhorn-critical
            # for the setting priority-class. Don't reset it to empty (which is
            # the default value defined in longhorn-manager code) because this will
            # restart Longhorn managed components and fail the test cases.
            # https://github.com/longhorn/longhorn/issues/7413#issuecomment-1881707958
            if setting.name == "priority-class":
                continue

            # The version of the support bundle kit will be specified by a command
            # option when starting the manager. And setting requires a value.
            #
            # Longhorn has a default version for each release provided to the
            # manager when starting. Meaning this setting doesn't have a default
            # value.
            #
            # The design grants the ability to update later by cases for
            # troubleshooting purposes. Meaning this setting is editable.
            #
            # So we need to skip here to avoid test failure when resetting this to
            # an empty default value.
            if setting_name == "support-bundle-manager-image":
                continue

            if setting_name == "registry-secret":
                continue

            s = client.by_id_setting(setting_name)
            if s.value != setting_default_value and not setting_readonly:
                try:
                    client.update(s, value=setting_default_value)
                except Exception as e:
                    logging(f"Failed to reset {setting_name} to {setting_default_value}: {e}")
