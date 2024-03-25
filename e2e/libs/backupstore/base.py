from abc import ABC, abstractmethod
import os
import time
import hashlib

SETTING_BACKUP_TARGET = "backup-target"
SETTING_BACKUP_TARGET_CREDENTIAL_SECRET = "backup-target-credential-secret"
SETTING_BACKUPSTORE_POLL_INTERVAL = "backupstore-poll-interval"

BACKUPSTORE_BV_PREFIX = "/backupstore/volumes/"
BACKUPSTORE_LOCK_DURATION = 150

RETRY_COUNT = 300
RETRY_INTERVAL = 1

class Base(ABC):

    def is_backupTarget_s3(self, s):
        return s.startswith("s3://")

    def is_backupTarget_nfs(self, s):
        return s.startswith("nfs://")

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

    @abstractmethod
    def set_backupstore(self, client):
        return NotImplemented

    def reset_backupstore_setting(self, client):
        backup_target_setting = client.by_id_setting(SETTING_BACKUP_TARGET)
        client.update(backup_target_setting, value="")

        backup_target_credential_setting = client.by_id_setting(
            SETTING_BACKUP_TARGET_CREDENTIAL_SECRET)
        client.update(backup_target_credential_setting, value="")

        backup_store_poll_interval = client.by_id_setting(
            SETTING_BACKUPSTORE_POLL_INTERVAL)
        client.update(backup_store_poll_interval, value="300")

    def set_backupstore_url(self, client, url):
        backup_target_setting = client.by_id_setting(SETTING_BACKUP_TARGET)
        backup_target_setting = client.update(backup_target_setting,
                                              value=url)
        assert backup_target_setting.value == url

    def set_backupstore_credential_secret(self, client, credential_secret):
        backup_target_credential_setting = client.by_id_setting(
            SETTING_BACKUP_TARGET_CREDENTIAL_SECRET)
        backup_target_credential_setting = client.update(
            backup_target_credential_setting, value=credential_secret)
        assert backup_target_credential_setting.value == credential_secret

    def set_backupstore_poll_interval(self, client, poll_interval):
        backup_store_poll_interval_setting = client.by_id_setting(
            SETTING_BACKUPSTORE_POLL_INTERVAL)
        backup_target_poll_interal_setting = client.update(
            backup_store_poll_interval_setting, value=poll_interval)
        assert backup_target_poll_interal_setting.value == poll_interval

    def backup_volume_path(self, volume_name):
        volume_name_sha512 = \
            hashlib.sha512(volume_name.encode('utf-8')).hexdigest()

        volume_dir_level_1 = volume_name_sha512[0:2]
        volume_dir_level_2 = volume_name_sha512[2:4]

        backupstore_bv_path = BACKUPSTORE_BV_PREFIX + \
            volume_dir_level_1 + "/" + \
            volume_dir_level_2 + "/" + \
            volume_name

        return backupstore_bv_path

    @abstractmethod
    def get_backup_volume_prefix(self, client, volume_name):
        return NotImplemented

    def get_backup_target(self, client):
        backup_target_setting = client.by_id_setting(SETTING_BACKUP_TARGET)
        return backup_target_setting.value

    def get_secret(self, client):
        backup_target_credential_setting = client.by_id_setting(
            SETTING_BACKUP_TARGET_CREDENTIAL_SECRET)
        return backup_target_credential_setting.value

    @abstractmethod
    def get_backup_cfg_file_path(self, client, volume_name, backup_name):
        return NotImplemented

    @abstractmethod
    def get_volume_cfg_file_path(self, client, volume_name):
        return NotImplemented

    @abstractmethod
    def get_backup_blocks_dir(self, client, volume_name):
        return NotImplemented

    @abstractmethod
    def create_file_in_backupstore(self):
        return NotImplemented

    @abstractmethod
    def write_backup_cfg_file(self, client, core_api, volume_name, backup_name, data):
        return NotImplemented

    @abstractmethod
    def delete_file_in_backupstore(self):
        return NotImplemented

    @abstractmethod
    def delete_backup_cfg_file(self):
        return NotImplemented

    @abstractmethod
    def delete_volume_cfg_file(self):
        return NotImplemented

    @abstractmethod
    def delete_random_backup_block(self):
        return NotImplemented

    @abstractmethod
    def count_backup_block_files(self):
        return NotImplemented

    def wait_for_lock_expiration(self):
        """
        waits 150 seconds which is the lock duration
        TODO: once we have implemented the delete functions,
              we can switch to removing the locks directly
        """
        time.sleep(BACKUPSTORE_LOCK_DURATION)

    def delete_backup_volume(self, client, volume_name):
        bv = client.by_id_backupVolume(volume_name)
        client.delete(bv)
        self.wait_for_backup_volume_delete(client, volume_name)

    def wait_for_backup_volume_delete(self, client, name):
        for _ in range(RETRY_COUNT):
            bvs = client.list_backupVolume()
            found = False
            for bv in bvs:
                if bv.name == name:
                    found = True
                    break
            if not found:
                break
            time.sleep(RETRY_INTERVAL)
        assert not found

    def cleanup_backup_volumes(self, client):
        backup_volumes = client.list_backup_volume()

        # we delete the whole backup volume, which skips block gc
        for backup_volume in backup_volumes:
            self.delete_backup_volume(client, backup_volume.name)

        backup_volumes = client.list_backup_volume()
        assert backup_volumes.data == []

    def cleanup_system_backups(self, client):
        """
        Clean up all system backups
        :param client: The Longhorn client to use in the request.
        """

        system_backups = client.list_system_backup()
        for system_backup in system_backups:
            # ignore the error when clean up
            try:
                client.delete(system_backup)
            except Exception as e:
                name = system_backup['name']
                print("\nException when cleanup system backup ", name)
                print(e)

        ok = False
        for _ in range(RETRY_COUNT):
            system_backups = client.list_system_backup()
            if len(system_backups) == 0:
                ok = True
                break
            time.sleep(RETRY_INTERVAL)
        assert ok