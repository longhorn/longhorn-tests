from abc import ABC, abstractmethod
import time
import os
import hashlib
from utility.utility import get_retry_count_and_interval
from setting import Setting

class Base(ABC):

    def is_backupTarget_s3(self, s):
        return s.startswith("s3://")

    def is_backupTarget_nfs(self, s):
        return s.startswith("nfs://")

    @classmethod
    def get_backupstores(cls):
        backupstore = os.environ['LONGHORN_BACKUPSTORES']
        backupstore = backupstore.replace(" ", "")
        backupstores = backupstore.split(",")
        for i in range(len(backupstores)):
            backupstores[i] = backupstores[i].split(":")[0]
        return backupstores

    def backup_volume_path(self, volume_name):
        volume_name_sha512 = \
            hashlib.sha512(volume_name.encode('utf-8')).hexdigest()

        volume_dir_level_1 = volume_name_sha512[0:2]
        volume_dir_level_2 = volume_name_sha512[2:4]

        backupstore_bv_path = "/backupstore/volumes/" + \
            volume_dir_level_1 + "/" + \
            volume_dir_level_2 + "/" + \
            volume_name

        return backupstore_bv_path

    @abstractmethod
    def get_backup_volume_prefix(self, client, volume_name):
        return NotImplemented

    def get_backup_target(self):
        return Setting().get_backup_target()

    def get_secret(self):
        return Setting().get_secret()

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

    def delete_backup_volume(self, client, volume_name):
        bv = client.by_id_backupVolume(volume_name)
        client.delete(bv)
        self.wait_for_backup_volume_delete(client, volume_name)

    def wait_for_backup_volume_delete(self, client, name):
        retry_count, retry_interval = get_retry_count_and_interval()
        for _ in range(retry_count):
            bvs = client.list_backupVolume()
            found = False
            for bv in bvs:
                if bv.name == name:
                    found = True
                    break
            if not found:
                break
            time.sleep(retry_interval)
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
        retry_count, retry_interval = get_retry_count_and_interval()
        for _ in range(retry_count):
            system_backups = client.list_system_backup()
            if len(system_backups) == 0:
                ok = True
                break
            time.sleep(retry_interval)
        assert ok
