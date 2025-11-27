from abc import ABC, abstractmethod

from utility.utility import set_annotation
from utility.utility import get_annotation_value
import utility.constant as constant

class Base(ABC):

    ANNOT_ID = "test.longhorn.io/snapshot-id"

    @abstractmethod
    def create(self, volume_name, snapshot_id, waiting):
        return NotImplemented

    def set_snapshot_id(self, snapshot_name, snapshot_id):
        set_annotation(
            group="longhorn.io",
            version="v1beta2",
            namespace=constant.LONGHORN_NAMESPACE,
            plural="snapshots",
            name=snapshot_name,
            annotation_key=self.ANNOT_ID,
            annotation_value=snapshot_id
        )

    def get_snapshot_id(self, snapshot_name):
        return get_annotation_value(
            group="longhorn.io",
            version="v1beta2",
            namespace=constant.LONGHORN_NAMESPACE,
            plural="snapshots",
            name=snapshot_name,
            annotation_key=self.ANNOT_ID
        )

    @abstractmethod
    def get(self, volume_name, snapshot_id):
        return NotImplemented

    @abstractmethod
    def get_volume_head(self, volume_name):
        return NotImplemented

    @abstractmethod
    def list(self, volume_name):
        return NotImplemented

    @abstractmethod
    def delete(self, volume_name, snapshot_id):
        return NotImplemented

    @abstractmethod
    def revert(self, volume_name, snapshot_id):
        return NotImplemented

    @abstractmethod
    def purge(self, volume_name):
        return NotImplemented

    @abstractmethod
    def is_parent_of(self, volume_name, parent_id, child_id):
        return NotImplemented

    @abstractmethod
    def is_parent_of_volume_head(self, volume_name, parent_id):
        return NotImplemented

    @abstractmethod
    def is_existing(self, volume_name, snapshot_id):
        return NotImplemented

    @abstractmethod
    def is_marked_as_removed(self, volume_name, snapshot_id):
        return NotImplemented

    @abstractmethod
    def get_checksum(self, volume_name, snapshot_id):
        return NotImplemented
