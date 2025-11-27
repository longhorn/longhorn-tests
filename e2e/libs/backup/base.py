from abc import ABC, abstractmethod

from utility.utility import set_annotation
from utility.utility import get_annotation_value
import utility.constant as constant


class Base(ABC):

    ANNOT_ID = "test.longhorn.io/backup-id"
    ANNOT_DATA_CHECKSUM = "test.longhorn.io/data-checksum"

    @abstractmethod
    def create(self, volume_name, backup_id, wait):
        return NotImplemented

    def set_backup_id(self, backup_name, backup_id):
        set_annotation(
            group="longhorn.io",
            version="v1beta2",
            namespace=constant.LONGHORN_NAMESPACE,
            plural="backups",
            name=backup_name,
            annotation_key=self.ANNOT_ID,
            annotation_value=backup_id
        )

    def get_backup_id(self, backup_name):
        return get_annotation_value(
            group="longhorn.io",
            version="v1beta2",
            namespace=constant.LONGHORN_NAMESPACE,
            plural="backups",
            name=backup_name,
            annotation_key=self.ANNOT_ID
        )

    def set_data_checksum(self, backup_name, checksum):
        set_annotation(
            group="longhorn.io",
            version="v1beta2",
            namespace=constant.LONGHORN_NAMESPACE,
            plural="backups",
            name=backup_name,
            annotation_key=self.ANNOT_DATA_CHECKSUM,
            annotation_value=checksum
        )

    def get_data_checksum(self, backup_name):
        return get_annotation_value(
            group="longhorn.io",
            version="v1beta2",
            namespace=constant.LONGHORN_NAMESPACE,
            plural="backups",
            name=backup_name,
            annotation_key=self.ANNOT_DATA_CHECKSUM,
        )

    @abstractmethod
    def get(self, backup_id, volume_name):
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
    def list_all(self):
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
    def check_restored_volume_checksum(self, volume_name, backup_name):
        return NotImplemented

    @abstractmethod
    def get_restored_checksum(self, backup_name):
        return NotImplemented

    @abstractmethod
    def cleanup_backup_volumes(self):
        return NotImplemented

    @abstractmethod
    def cleanup_backups(self):
        return NotImplemented