from system_backup.base import Base

import time
import json

from kubernetes import client
from kubernetes.client.rest import ApiException

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

    def set_system_backup_status(self, backup_name, status):
        logging(f"Setting system backup {backup_name} status to {status}")
        return client.CustomObjectsApi().patch_namespaced_custom_object_status(
            group="longhorn.io", version="v1beta2",
            namespace=constant.LONGHORN_NAMESPACE, plural="systembackups",
            name=backup_name, body={"status": status})

    def check_system_backup_created_at_empty(self, backup_name):
        backup = client.CustomObjectsApi().get_namespaced_custom_object(
            group="longhorn.io", version="v1beta2",
            namespace=constant.LONGHORN_NAMESPACE, plural="systembackups",
            name=backup_name)
        created_at = backup.get('status', {}).get('createdAt')
        assert created_at in (None, ""), f"System backup {backup_name} createdAt is not empty: {created_at}"

    def wait_for_system_backup_deleted(self, backup_name):
        api = client.CustomObjectsApi()
        for i in range(self.retry_count):
            logging(f"Waiting for system backup {backup_name} deleted ... ({i})")
            try:
                api.get_namespaced_custom_object(
                    group="longhorn.io", version="v1beta2",
                    namespace=constant.LONGHORN_NAMESPACE, plural="systembackups",
                    name=backup_name)
            except ApiException as e:
                if e.status == 404:
                    return
                raise
            time.sleep(self.retry_interval)
        assert False, f"Failed to wait for system backup {backup_name} deleted"
