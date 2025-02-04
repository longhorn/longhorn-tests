from kubernetes import client
from backup.base import Base
from utility.utility import logging

class CRD(Base):

    def __init__(self):
        self.obj_api = client.CustomObjectsApi()

    def create(self, volume_name, backup_id, wait):
        return NotImplemented

    def get(self, backup_id, volume_name):
        return NotImplemented

    def get_from_list(self, backup_list, backup_id):
        return NotImplemented

    def get_by_snapshot(self, volume_name, snapshot_name):
        return NotImplemented

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
                                                             "longhorn-system",
                                                             "backups")
        for backup in backups['items']:
            logging(f"Deleting backup {backup['metadata']['name']}")
            try:
                self.obj_api.delete_namespaced_custom_object("longhorn.io",
                                                             "v1beta2",
                                                             "longhorn-system",
                                                             "backups",
                                                             backup['metadata']['name'])
            except Exception as e:
                if e.reason != "Not Found":
                    Exception(f"Deleting backup failed: {e}")

    def cleanup_system_backups(self):
        return NotImplemented