from backupstore.base import Base
import os
import subprocess
from urllib.parse import urlparse

class Nfs(Base):

    def mount_nfs_backupstore(self, client, mount_path="/mnt/nfs"):
        cmd = ["mkdir", "-p", mount_path]
        subprocess.check_output(cmd)
        nfs_backuptarget = client.by_id_setting(SETTING_BACKUP_TARGET).value
        nfs_url = urlparse(nfs_backuptarget).netloc + \
            urlparse(nfs_backuptarget).path
        cmd = ["mount", "-t", "nfs", "-o", "nfsvers=4.2", nfs_url, mount_path]
        subprocess.check_output(cmd)

    def umount_nfs_backupstore(self, client, mount_path="/mnt/nfs"):
        cmd = ["umount", mount_path]
        subprocess.check_output(cmd)
        cmd = ["rmdir", mount_path]
        subprocess.check_output(cmd)

    def get_nfs_mount_point(self, client):
        nfs_backuptarget = client.by_id_setting(SETTING_BACKUP_TARGET).value
        nfs_url = urlparse(nfs_backuptarget).netloc + \
            urlparse(nfs_backuptarget).path

        cmd = ["findmnt", "-t", "nfs4", "-n", "--output", "source,target"]
        stdout = subprocess.run(cmd, capture_output=True).stdout
        mount_info = stdout.decode().strip().split(" ")

        assert mount_info[0] == nfs_url
        return mount_info[1]

    def get_backup_volume_prefix(self, client, volume_name):
        mount_point = self.get_nfs_mount_point(client)
        return mount_point + self.backup_volume_path(volume_name)

    def get_backup_cfg_file_path(self, client, volume_name, backup_name):
        prefix = self.get_backup_volume_prefix(client, volume_name)
        return prefix + "/backups/backup_" + backup_name + ".cfg"

    def get_volume_cfg_file_path(self, client, volume_name):
        prefix = self.get_backup_volume_prefix(client, volume_name)
        return prefix + "/volume.cfg"

    def get_backup_blocks_dir(self, client, volume_name):
        prefix = self.get_backup_volume_prefix(client, volume_name)
        return prefix + "/blocks"

    def create_file_in_backupstore(self, file_path, data={}):
        with open(file_path, 'w') as cfg_file:
            cfg_file.write(str(data))

    def write_backup_cfg_file(self, client, volume_name, backup_name, data):
        nfs_backup_cfg_file_path = self.get_backup_cfg_file_path(client,
                                                                 volume_name,
                                                                 backup_name)
        with open(nfs_backup_cfg_file_path, 'w') as cfg_file:
            cfg_file.write(str(data))

    def delete_file_in_backupstore(self, file_path):
        try:
            os.remove(file_path)
        except Exception as ex:
            print("error while deleting file:",
                  file_path)
            print(ex)

    def delete_backup_cfg_file(self, client, volume_name, backup_name):
        nfs_backup_cfg_file_path = self.get_backup_cfg_file_path(client,
                                                                 volume_name,
                                                                 backup_name)
        try:
            os.remove(nfs_backup_cfg_file_path)
        except Exception as ex:
            print("error while deleting backup cfg file:",
                  nfs_backup_cfg_file_path)
            print(ex)

    def delete_volume_cfg_file(self, client, volume_name):
        nfs_volume_cfg_path = self.get_volume_cfg_file_path(client, volume_name)
        try:
            os.remove(nfs_volume_cfg_path)
        except Exception as ex:
            print("error while deleting backup cfg file:", nfs_volume_cfg_path)
            print(ex)

    def delete_random_backup_block(self, client, volume_name):
        backup_blocks_dir = self.get_backup_blocks_dir(client, volume_name)
        cmd = ["find", backup_blocks_dir, "-type", "f"]
        find_cmd = subprocess.Popen(cmd, stdout=subprocess.PIPE)
        head_cmd = subprocess.check_output(["/usr/bin/head", "-1"], stdin=find_cmd.stdout)
        backup_block_file_path = head_cmd.decode().strip()

        try:
            os.remove(backup_block_file_path)
        except Exception as ex:
            print("error while deleting backup block file:",
                  backup_block_file_path)
            print(ex)

    def count_backup_block_files(self, client, volume_name):
        backup_blocks_dir = self.get_backup_blocks_dir(client, volume_name)
        cmd = ["find", backup_blocks_dir, "-type", "f"]
        find_cmd = subprocess.Popen(cmd, stdout=subprocess.PIPE)
        wc_cmd = subprocess.check_output(["/usr/bin/wc", "-l"], stdin=find_cmd.stdout)
        backup_blocks_count = int(wc_cmd.decode().strip())

        return backup_blocks_count

    def cleanup_backup_volumes(self, client):
        super().cleanup_backup_volumes(client)
        self.umount_nfs_backupstore(client)
