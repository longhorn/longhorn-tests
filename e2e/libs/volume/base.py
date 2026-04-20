from abc import ABC, abstractmethod
import time

from persistentvolume.persistentvolume import PersistentVolume
from persistentvolumeclaim.persistentvolumeclaim import PersistentVolumeClaim
from utility.utility import set_annotation
from utility.utility import get_annotation_value
from utility.utility import logging
from utility.utility import get_retry_count_and_interval
from utility.utility import convert_size_to_bytes
import utility.constant as constant


class Base(ABC):

    ANNOT_DATA_CHECKSUM = "test.longhorn.io/data-checksum-"
    ANNOT_LAST_CHECKSUM = "test.longhorn.io/last-recorded-checksum"

    def __init__(self):
        self.retry_count, self.retry_interval = get_retry_count_and_interval()
        self.pv = PersistentVolume()
        self.pvc = PersistentVolumeClaim()

    def _get_volume_size(self, volume):
        # CRD returns dict-like payloads, REST returns object-like payloads.
        if isinstance(volume, dict):
            return volume.get("size") or volume.get("spec", {}).get("size")
        return getattr(volume, "size", None)

    @abstractmethod
    def get(self, volume_name):
        return NotImplemented

    @abstractmethod
    def create(self, volume_name, size, numberOfReplicas, frontend, migratable, accessMode, dataEngine, backingImage, Standby, fromBackup, encrypted, rebuildConcurrentSyncLimit):
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
    def prefill_with_fio(self, volume_name, size):
        return NotImplemented

    @abstractmethod
    def write_scattered_data_with_fio(self, volume_name, size, bs, ratio):
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

    def create_persistentvolume(self, volume_name, retry, volumeMode, fsType):
        logging(f'Creating PV {volume_name} for volume {volume_name}')
        volume = self.get(volume_name)
        volume_size = self._get_volume_size(volume)
        assert volume_size is not None, f"Cannot determine size for volume {volume_name}"
        storage = str(convert_size_to_bytes(str(volume_size)))
        self.pv.create(volume_name, storage, volumeMode, fsType)

        if not retry:
            return

        created = False
        for _ in range(self.retry_count):
            if self.pv.is_exist(volume_name):
                created = True
                break
            time.sleep(self.retry_interval)
        assert created

    def create_persistentvolumeclaim(self, volume_name, volumeMode, retry):
        logging(f'Creating PVC {volume_name} for volume {volume_name}')
        volume = self.get(volume_name)
        volume_size = self._get_volume_size(volume)
        assert volume_size is not None, f"Cannot determine size for volume {volume_name}"
        storage = str(convert_size_to_bytes(str(volume_size)))
        self.pvc.create(volume_name, "RWO", "longhorn", storage_size=storage, volume_name=volume_name, volumeMode=volumeMode)

        if not retry:
            return

        created = False
        for _ in range(self.retry_count):
            if self.pvc.is_exist(volume_name, namespace="default"):
                created = True
                break
            time.sleep(self.retry_interval)
        assert created
