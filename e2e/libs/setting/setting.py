import os
import time

from utility.utility import get_longhorn_client
from utility.utility import get_retry_count_and_interval
from utility.utility import logging
from utility.constant import DEFAULT_BACKUPSTORE


class Setting:

    SETTING_BACKUP_TARGET = "backup-target"
    SETTING_BACKUP_TARGET_CREDENTIAL_SECRET = "backup-target-credential-secret"
    SETTING_BACKUPSTORE_POLL_INTERVAL = "backupstore-poll-interval"

    SETTING_BACKUP_TARGET_NOT_SUPPORTED = \
        f"setting {SETTING_BACKUP_TARGET} is not supported"
    SETTING_BACKUP_TARGET_CREDENTIAL_SECRET_NOT_SUPPORTED = \
        f"setting {SETTING_BACKUP_TARGET_CREDENTIAL_SECRET} is not supported"
    SETTING_SETTING_BACKUPSTORE_POLL_INTERVAL_NOT_SUPPORTED = \
        f"setting {SETTING_BACKUPSTORE_POLL_INTERVAL} is not supported"

    def __init__(self):
        self.retry_count, self.retry_interval = get_retry_count_and_interval()

    def _update_setting(self, key, value):
        setting = get_longhorn_client().by_id_setting(key)
        get_longhorn_client().update(setting, value=value)

    def update_setting(self, key, value, retry=True):
        logging(f"Trying to update setting {key} to {value} ...")
        if retry:
            logging(
                f"Retrying {self.retry_count} times with "
                f"{self.retry_interval} seconds interval."
            )
            for i in range(self.retry_count):
                try:
                    self._update_setting(key, value)
                    return
                except Exception as e:
                    logging(
                        f"Retrying to update setting {key} to {value} ... "
                        f"({i + 1})"
                    )
                    # Failed if it is the last retry
                    if i == self.retry_count - 1:
                        logging(
                            f"Failed to update setting {key} to {value} after "
                            f"{self.retry_count} attempts: {e}"
                        )
                        raise
                    else:
                        logging(
                            f"Retrying to update setting {key} to {value} ... "
                            f"(attempt {i + 1})"
                        )
                        time.sleep(self.retry_interval)
        else:
            self._update_setting(key, value)

    def get_setting(self, key):
        return get_longhorn_client().by_id_setting(key).value

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
                for i in range(self.retry_count):
                    logging(f"Try to reset {setting_name} to {setting_default_value} ... ({i})")
                    try:
                        client.update(s, value=setting_default_value)
                        break
                    except Exception as e:
                        logging(f"Failed to reset {setting_name} to {setting_default_value}: {e}")
                    time.sleep(self.retry_interval)
