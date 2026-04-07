from abc import ABC, abstractmethod
import hashlib
import os
import re
import time
import json

from kubernetes import client

from utility.utility import get_longhorn_client
from utility.utility import logging
from utility.utility import get_retry_count_and_interval
from utility.utility import subprocess_exec_cmd
from utility.constant import DEFAULT_BACKUPSTORE
from utility import constant

SECOND = 1
MINUTE = 60 * SECOND
HOUR = 60 * MINUTE

duration_u = {
    "s":  SECOND,
    "m":  MINUTE,
    "h":  HOUR,
}


def from_k8s_duration_to_seconds(duration_s):
    # k8s duration string format such as "3h5m30s"
    total = 0
    pattern_str = r'([0-9]+)([smh]+)'
    pattern = re.compile(pattern_str)
    matches = pattern.findall(duration_s)
    if not len(matches):
        raise Exception("Invalid duration {}".format(duration_s))

    for v, u in matches:
        total += int(v) * duration_u[u]

    return total


class Base(ABC):

    DEFAULT_BACKUPTARGET = "default"

    def __init__(self):
        self.retry_count, self.retry_interval = get_retry_count_and_interval()
        self.core_api = client.CoreV1Api()
        backupstore = os.environ.get('LONGHORN_BACKUPSTORE', DEFAULT_BACKUPSTORE)

        if not backupstore:
            return

        backupsettings = backupstore.split("$")
        self.backup_target = backupsettings[0]
        self.secret = backupsettings[1] if len(backupsettings) > 1 else ""

    def is_backupTarget_s3(self, s):
        return s.startswith("s3://")

    def is_backupTarget_nfs(self, s):
        return s.startswith("nfs://")

    def is_backupTarget_cifs(self, s):
        return s.startswith("cifs://")

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

    def get_backupstore_url(self):
        return get_longhorn_client().by_id_backupTarget(
                            self.DEFAULT_BACKUPTARGET).backupTargetURL

    def get_backupstore_secret(self):
        return get_longhorn_client().by_id_backupTarget(
                            self.DEFAULT_BACKUPTARGET).credentialSecret

    def get_backupstore_poll_interval(self):
        k8s_duration = get_longhorn_client().by_id_backupTarget(
                            self.DEFAULT_BACKUPTARGET).pollInterval
        return from_k8s_duration_to_seconds(k8s_duration)

    def set_backupstore(self):
        backupstore = os.environ.get('LONGHORN_BACKUPSTORE', DEFAULT_BACKUPSTORE)
        if backupstore:
            backupsettings = backupstore.split("$")
            url = backupsettings[0]
            secret = backupsettings[1] if len(backupsettings) > 1 else ""
            poll_interval = os.environ.get('LONGHORN_BACKUPSTORE_POLL_INTERVAL', '30s')
            self.set_default_backuptarget(url, secret, poll_interval)
            self.wait_for_backupstore_available()

    def set_default_backuptarget(self, url, secret, poll_interval):
        setting = {"spec": {"backupTargetURL": url, "credentialSecret": secret, "pollInterval": poll_interval}}
        cmd = "kubectl patch backuptarget -n {} {} --type='merge' -p '{}'".format(
            constant.LONGHORN_NAMESPACE,
            self.DEFAULT_BACKUPTARGET,
            json.dumps(setting)
        )
        for i in range(self.retry_count):
            logging(f"Setting default backuptarget to {setting} ... ({i})")
            try:
                subprocess_exec_cmd(cmd)
                return
            except Exception as e:
                logging(f"Failed to set default backuptarget to {setting}: {e}")
            time.sleep(self.retry_interval)
        assert False, f"Failed to set default backuptarget to {setting}"

    def set_backupstore_url(self, url):
        cmd = "kubectl patch backuptarget -n {} {} --type='merge' -p '{}'".format(
            constant.LONGHORN_NAMESPACE,
            self.DEFAULT_BACKUPTARGET,
            json.dumps({"spec": {"backupTargetURL": url}})
        )
        for i in range(self.retry_count):
            logging(f"Setting backupstore url to {url} ... ({i})")
            try:
                subprocess_exec_cmd(cmd)
                return
            except Exception as e:
                logging(f"Failed to set backupstore url to {url}: {e}")
            time.sleep(self.retry_interval)
        assert False, f"Failed to set backupstore url to {url}"

    def set_backupstore_secret(self, secret):
        cmd = "kubectl patch backuptarget -n {} {} --type='merge' -p '{}'".format(
            constant.LONGHORN_NAMESPACE,
            self.DEFAULT_BACKUPTARGET,
            json.dumps({"spec": {"credentialSecret": secret}})
        )
        for i in range(self.retry_count):
            logging(f"Setting backupstore secret to {secret} ... ({i})")
            try:
                subprocess_exec_cmd(cmd)
                return
            except Exception as e:
                logging(f"Failed to set backupstore secret to {secret}: {e}")
            time.sleep(self.retry_interval)
        assert False, f"Failed to set backupstore secret to {secret}"


    def set_backupstore_poll_interval(self, poll_interval):
        cmd = "kubectl patch backuptarget -n {} {} --type='merge' -p '{}'".format(
            constant.LONGHORN_NAMESPACE,
            self.DEFAULT_BACKUPTARGET,
            json.dumps({"spec": {"pollInterval": poll_interval}})
        )
        for i in range(self.retry_count):
            logging(f"Setting backupstore poll interval to {poll_interval} ... ({i})")
            try:
                subprocess_exec_cmd(cmd)
                return
            except Exception as e:
                logging(f"Failed to set backupstore poll interval to {poll_interval}: {e}")
            time.sleep(self.retry_interval)
        assert False, f"Failed to set backupstore poll interval to {poll_interval}"

    def wait_for_backupstore_available(self):
        for i in range(self.retry_count):
            logging(f"Waiting for default backupstore available ... ({i})")
            try:
                bt = get_longhorn_client().by_id_backupTarget(self.DEFAULT_BACKUPTARGET)
                if bt.available:
                    return
            except Exception as e:
                logging(f"Failed to get default backupstore: {e}")
            time.sleep(self.retry_interval)
        assert False, f"Failed to wait for default backupstore available"

    def reset_backupstore(self):
        self.set_default_backuptarget("", "", "5m0s")

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

    def extract_dummy_backup(self, filename):
        filepath = f"./templates/backup/{filename}"
        subprocess_exec_cmd(["tar", "-xzvf", filepath])

    @abstractmethod
    def create_dummy_backup(self, filename):
        return NotImplemented


class BackupStore(Base):

    def __init__(self):
        super().__init__()

    def get_backup_volume_prefix(self, volume_name):
        return NotImplemented

    def get_backup_cfg_file_path(self, volume_name, backup_name):
        return NotImplemented

    def get_volume_cfg_file_path(self, volume_name):
        return NotImplemented

    def get_backup_blocks_dir(self, volume_name):
        return NotImplemented

    def create_file_in_backupstore(self):
        return NotImplemented

    def write_backup_cfg_file(self, volume_name, backup_name, data):
        return NotImplemented

    def delete_file_in_backupstore(self):
        return NotImplemented

    def delete_backup_cfg_file(self):
        return NotImplemented

    def delete_volume_cfg_file(self):
        return NotImplemented

    def delete_random_backup_block(self):
        return NotImplemented

    def count_backup_block_files(self):
        return NotImplemented

    def create_dummy_backup(self, filename):
        return NotImplemented
