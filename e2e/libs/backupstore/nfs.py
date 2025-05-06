import os
import subprocess
import time

from workload.workload import get_workload_pod_names
from utility.utility import subprocess_exec_cmd
from utility.utility import logging

from backupstore.base import Base

from urllib.parse import urlparse

class Nfs(Base):

    def __init__(self):
        super().__init__()
        self.mount_nfs_backupstore()

    def mount_nfs_backupstore(self, mount_path="/mnt/nfs"):
        cmd = ["mkdir", "-p", mount_path]
        subprocess.check_output(cmd)
        nfs_backuptarget = self.backup_target
        nfs_url = urlparse(nfs_backuptarget).netloc + \
            urlparse(nfs_backuptarget).path
        cmd = ["mount", "-t", "nfs", "-o", "nfsvers=4.2", nfs_url, mount_path]
        subprocess.check_output(cmd)

    def umount_nfs_backupstore(self, mount_path="/mnt/nfs"):
        cmd = ["umount", mount_path]
        subprocess.check_output(cmd)
        cmd = ["rmdir", mount_path]
        subprocess.check_output(cmd)

    def get_nfs_mount_point(self):
        nfs_backuptarget = self.backup_target
        nfs_url = urlparse(nfs_backuptarget).netloc + \
            urlparse(nfs_backuptarget).path

        cmd = ["findmnt", "-t", "nfs4", "-n", "--output", "source,target"]
        stdout = subprocess.run(cmd, capture_output=True).stdout
        mount_info = stdout.decode().strip().split(" ")

        assert mount_info[0] == nfs_url
        return mount_info[1]

    def get_backup_volume_prefix(self, volume_name):
        mount_point = self.get_nfs_mount_point()
        return mount_point + self.backup_volume_path(volume_name)

    def get_backup_cfg_file_path(self, volume_name, backup_name):
        prefix = self.get_backup_volume_prefix(volume_name)
        return prefix + "/backups/backup_" + backup_name + ".cfg"

    def get_volume_cfg_file_path(self, volume_name):
        prefix = self.get_backup_volume_prefix(volume_name)
        return prefix + "/volume.cfg"

    def get_backup_blocks_dir(self, volume_name):
        prefix = self.get_backup_volume_prefix(volume_name)
        return prefix + "/blocks"

    def create_file_in_backupstore(self, file_path, data={}):
        with open(file_path, 'w') as cfg_file:
            cfg_file.write(str(data))

    def write_backup_cfg_file(self, volume_name, backup_name, data):
        nfs_backup_cfg_file_path = self.get_backup_cfg_file_path(volume_name,
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

    def delete_backup_cfg_file(self, volume_name, backup_name):
        nfs_backup_cfg_file_path = self.get_backup_cfg_file_path(volume_name,
                                                                 backup_name)
        try:
            os.remove(nfs_backup_cfg_file_path)
        except Exception as ex:
            print("error while deleting backup cfg file:",
                  nfs_backup_cfg_file_path)
            print(ex)

    def delete_volume_cfg_file(self, volume_name):
        nfs_volume_cfg_path = self.get_volume_cfg_file_path(volume_name)
        try:
            os.remove(nfs_volume_cfg_path)
        except Exception as ex:
            print("error while deleting backup cfg file:", nfs_volume_cfg_path)
            print(ex)

    def delete_random_backup_block(self, volume_name):
        backup_blocks_dir = self.get_backup_blocks_dir(volume_name)
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

    def count_backup_block_files(self, volume_name):
        backup_blocks_dir = self.get_backup_blocks_dir(volume_name)
        cmd = ["find", backup_blocks_dir, "-type", "f"]
        find_cmd = subprocess.Popen(cmd, stdout=subprocess.PIPE)
        wc_cmd = subprocess.check_output(["/usr/bin/wc", "-l"], stdin=find_cmd.stdout)
        backup_blocks_count = int(wc_cmd.decode().strip())

        return backup_blocks_count

    def cleanup_backup_volumes(self):
        super().cleanup_backup_volumes()
        self.umount_nfs_backupstore()

    def create_dummy_backup(self, filename):
        logging(f"Creating dummy backup from file {filename}")
        self.extract_dummy_backup(filename)
        backupstore_pod_name = get_workload_pod_names("longhorn-test-nfs")[0]
        cmd = ["kubectl", "cp", "./backupstore", f"{backupstore_pod_name}:/opt/backupstore"]
        subprocess_exec_cmd(cmd)
        cmd = ["rm", "-rf", "./backupstore"]
        subprocess_exec_cmd(cmd)
        # wait for backup sync by sleeping for the poll interval
        time.sleep(30)
        logging(f"Created dummy backup from file {filename}")
