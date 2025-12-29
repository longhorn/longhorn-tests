from abc import ABC, abstractmethod

from utility.utility import set_annotation
from utility.utility import get_annotation_value
from utility.utility import logging
import utility.constant as constant


class Base(ABC):

    ANNOT_DATA_CHECKSUM = "test.longhorn.io/data-checksum-"
    ANNOT_LAST_CHECKSUM = "test.longhorn.io/last-recorded-checksum"

    @abstractmethod
    def get(self, volume_name):
        return NotImplemented

    @abstractmethod
    def create(self, volume_name, size, numberOfReplicas, frontend, migratable, accessMode, dataEngine, backingImage, Standby, fromBackup, encrypted):
        return NotImplemented

    def set_data_checksum(self, volume_name, data_id, checksum):
        set_annotation(
            group="longhorn.io",
            version="v1beta2",
            namespace=constant.LONGHORN_NAMESPACE,
            plural="volumes",
            name=volume_name,
            annotation_key=f"{self.ANNOT_DATA_CHECKSUM}{data_id}",
            annotation_value=checksum
        )

    def get_data_checksum(self, volume_name, data_id):
        return get_annotation_value(
            group="longhorn.io",
            version="v1beta2",
            namespace=constant.LONGHORN_NAMESPACE,
            plural="volumes",
            name=volume_name,
            annotation_key=f"{self.ANNOT_DATA_CHECKSUM}{data_id}",
        )

    def set_last_data_checksum(self, volume_name, checksum):
        set_annotation(
            group="longhorn.io",
            version="v1beta2",
            namespace=constant.LONGHORN_NAMESPACE,
            plural="volumes",
            name=volume_name,
            annotation_key=self.ANNOT_LAST_CHECKSUM,
            annotation_value=checksum
        )

    def get_last_data_checksum(self, volume_name):
        try:
            return get_annotation_value(
                group="longhorn.io",
                version="v1beta2",
                namespace=constant.LONGHORN_NAMESPACE,
                plural="volumes",
                name=volume_name,
                annotation_key=self.ANNOT_LAST_CHECKSUM,
            )
        except Exception as e:
            logging(f"Getting volume {volume_name} last data checksum failed: {e}")
            return ""

    @abstractmethod
    def attach(self, volume_name, node_name, disable_frontend, wait, retry):
        return NotImplemented

    @abstractmethod
    def is_attached_to(self, volume_name, node_name):
        return NotImplemented

    @abstractmethod
    def detach(self, volume_name, node_name):
        return NotImplemented

    @abstractmethod
    def delete(self, volume_name):
        return NotImplemented

    @abstractmethod
    def wait_for_volume_to_be_created(self, volume_name):
        return NotImplemented

    @abstractmethod
    def wait_for_volume_state(self, volume_name, desired_state):
        return NotImplemented

    @abstractmethod
    def wait_for_volume_migration_to_be_ready(self, volume_name):
        return NotImplemented

    @abstractmethod
    def wait_for_volume_migration_complete(self, volume_name, node_name):
        return NotImplemented

    @abstractmethod
    def wait_for_volume_migration_to_rollback(self, volume_name, node_name):
        return NotImplemented

    @abstractmethod
    def wait_for_volume_restoration_to_complete(self, volume_name, backup_name):
        return NotImplemented

    @abstractmethod
    def wait_for_volume_restoration_start(self, volume_name, backup_name):
        return NotImplemented

    @abstractmethod
    def get_endpoint(self, volume_name):
        return NotImplemented

    @abstractmethod
    def write_random_data(self, volume_name, size, data_id):
        return NotImplemented

    @abstractmethod
    def delete_replica(self, volume_name, node_name):
        return NotImplemented

    @abstractmethod
    def wait_for_replica_rebuilding_start(self, volume_name, node_name):
        return NotImplemented

    @abstractmethod
    def is_replica_rebuilding_in_progress(self, volume_name, node_name):
        return NotImplemented

    @abstractmethod
    def wait_for_replica_rebuilding_complete(self, volume_name, node_name):
        return NotImplemented

    @abstractmethod
    def check_data_checksum(self, volume_name, data_id):
        return NotImplemented

    @abstractmethod
    def get_checksum(self, volume_name):
        return NotImplemented

    @abstractmethod
    def activate(self, volume_name):
        return NotImplemented

    @abstractmethod
    def create_persistentvolume(self, volume_name, retry):
        return NotImplemented

    @abstractmethod
    def create_persistentvolumeclaim(self, volume_name, retry):
        return NotImplemented

    # @abstractmethod
    # def cleanup(self, volume_names):
    #     return NotImplemented
