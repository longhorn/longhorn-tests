from abc import ABC, abstractmethod
import hashlib
import os

from kubernetes import client


class Base(ABC):

    def __init__(self):
        self.core_api = client.CoreV1Api()
        backupstore = os.environ.get('LONGHORN_BACKUPSTORE')
        backupsettings = backupstore.split("$")
        self.backup_target = backupsettings[0]
        self.secret = backupsettings[1] if len(backupsettings) > 1 else ""

    def is_backupTarget_s3(self, s):
        return s.startswith("s3://")

    def is_backupTarget_nfs(self, s):
        return s.startswith("nfs://")

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
    def get_backup_volume_prefix(self, volume_name):
        return NotImplemented

    @abstractmethod
    def get_backup_cfg_file_path(self, volume_name, backup_name):
        return NotImplemented

    @abstractmethod
    def get_volume_cfg_file_path(self, volume_name):
        return NotImplemented

    @abstractmethod
    def get_backup_blocks_dir(self, volume_name):
        return NotImplemented

    @abstractmethod
    def create_file_in_backupstore(self):
        return NotImplemented

    @abstractmethod
    def write_backup_cfg_file(self, volume_name, backup_name, data):
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
