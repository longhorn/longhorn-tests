from system_backup.base import Base

import time
import json

from utility.utility import logging
from utility.utility import get_retry_count_and_interval
from utility.utility import subprocess_exec_cmd
import utility.constant as constant


class CRD(Base):

    def __init__(self):
        self.retry_count, self.retry_interval = get_retry_count_and_interval()

    def create(self, backup_name, backup_policy):
        return NotImplemented

    def restore(self, backup_name):
        return NotImplemented

    def get_by_name(self, backup_name):
        cmd = f"kubectl get systembackup {backup_name} -n {constant.LONGHORN_NAMESPACE} -ojson"
        try:
            return json.loads(subprocess_exec_cmd(cmd))
        except Exception as e:
            logging(f"Failed to get system backup {backup_name}: {e}")
            return None

    def wait_for_system_backup_ready(self, backup_name):
        for i in range(self.retry_count):
            logging(f"Waiting for system backup {backup_name} ready ... ({i})")
            backup = self.get_by_name(backup_name)
            if backup and backup['status']['state'] == "Ready":
                return
            time.sleep(self.retry_interval)
        assert False, f"Failed to wait for system backup {backup_name} ready"
