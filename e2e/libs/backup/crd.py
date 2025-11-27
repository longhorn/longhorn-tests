import json

from kubernetes import client
from backup.base import Base
from utility.utility import logging
from utility.utility import subprocess_exec_cmd
import utility.constant as constant

class CRD(Base):

    def __init__(self):
        self.obj_api = client.CustomObjectsApi()

    def create(self, volume_name, backup_id, wait, snapshot_id=None):
        return NotImplemented

    def get(self, backup_id, volume_name):
        return NotImplemented

    def get_from_list(self, backup_list, backup_id):
        return NotImplemented

    def get_by_snapshot(self, volume_name, snapshot_name):
        return NotImplemented

    # directly get backup CRD by its name
    # which is impossible through REST API
    # since a backup is bound to a backupvolume (/v1/backup/vol-name) or
    # a volume (/v1/volumes/vol-name) in REST API
    def get_by_name(self, backup_name):
        cmd = f"kubectl get backups {backup_name} -n {constant.LONGHORN_NAMESPACE} -ojson"
        try:
            return json.loads(subprocess_exec_cmd(cmd))
        except Exception as e:
            logging(f"Failed to get backup {backup_name}: {e}")
            return None

    def get_backup_volume(self, volume_name):
        return NotImplemented

    def wait_for_backup_completed(self, volume_name, snapshot_name):
        return NotImplemented

    def list(self, volume_name):
        return NotImplemented

    def list_all(self):
        return NotImplemented

    def assert_all_backups_before_uninstall_exist(self, backups_before_uninstall):
        return NotImplemented

    def delete(self, volume_name, backup_id):
        return NotImplemented

    def delete_backup_volume(self, volume_name):
        return NotImplemented

    def wait_for_backup_volume_delete(self, name):
        return NotImplemented

    def restore(self, volume_name, backup_id):
        return NotImplemented

    def check_restored_volume_checksum(self, volume_name, backup_name):
        return NotImplemented

    def get_restored_checksum(self, backup_name):
        return NotImplemented

    def cleanup_backup_volumes(self):
        return NotImplemented

    def cleanup_backups(self):
        # Use k8s api to delete all backup especially backup in error state
        # Because backup in error state does not have backup volume
        backups = self.obj_api.list_namespaced_custom_object("longhorn.io",
                                                             "v1beta2",
                                                             constant.LONGHORN_NAMESPACE,
                                                             "backups")
        for backup in backups['items']:
            logging(f"Deleting backup {backup['metadata']['name']}")
            try:
                self.obj_api.delete_namespaced_custom_object("longhorn.io",
                                                             "v1beta2",
                                                             constant.LONGHORN_NAMESPACE,
                                                             "backups",
                                                             backup['metadata']['name'])
            except Exception as e:
                if e.reason != "Not Found":
                    Exception(f"Deleting backup failed: {e}")
