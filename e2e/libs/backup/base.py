from abc import ABC, abstractmethod
from utility.utility import set_annotation
from utility.utility import get_annotation_value

class Base(ABC):

    ANNOT_ID = "test.longhorn.io/backup-id"

    @abstractmethod
    def create(self, volume_name, backup_id):
        return NotImplemented

    def set_backup_id(self, backup_name, backup_id):
        set_annotation(
            group="longhorn.io",
            version="v1beta2",
            namespace="longhorn-system",
            plural="backups",
            name=backup_name,
            annotation_key=self.ANNOT_ID,
            annotation_value=backup_id
        )

    def get_backup_id(self, backup_name):
        return get_annotation_value(
            group="longhorn.io",
            version="v1beta2",
            namespace="longhorn-system",
            plural="backups",
            name=backup_name,
            annotation_key=self.ANNOT_ID
        )

    @abstractmethod
    def get(self, volume_name, backup_id):
        return NotImplemented

    def get_by_snapshot(self, volume_name, snapshot_name):
        return NotImplemented

    @abstractmethod
    def get_backup_volume(self, volume_name):
        return NotImplemented

    def wait_for_backup_completed(self, volume_name, snapshot_name):
        return NotImplemented

    @abstractmethod
    def list(self, volume_name):
        return NotImplemented

    @abstractmethod
    def delete(self, volume_name, backup_id):
        return NotImplemented

    @abstractmethod
    def delete_backup_volume(self, volume_name):
        return NotImplemented

    @abstractmethod
    def restore(self, volume_name, backup_id):
        return NotImplemented

    @abstractmethod
    def cleanup_backup_volumes(self):
        return NotImplemented

    @abstractmethod
    def cleanup_system_backups(self):
        return NotImplemented
