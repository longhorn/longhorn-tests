from abc import ABC, abstractmethod
from utility.utility import set_annotation
from utility.utility import get_annotation_value


class Base(ABC):

    ANNOT_DATA_CHECKSUM = f'test.longhorn.io/data-checksum-'

    @abstractmethod
    def get(self, volume_name):
        return NotImplemented

    @abstractmethod
    def create(self, volume_name, size, replica_count):
        return NotImplemented

    def set_data_checksum(self, volume_name, data_id, checksum):
        set_annotation(
            group="longhorn.io",
            version="v1beta2",
            namespace="longhorn-system",
            plural="volumes",
            name=volume_name,
            annotation_key=f"{self.ANNOT_DATA_CHECKSUM}{data_id}",
            annotation_value=checksum
        )

    def get_data_checksum(self, volume_name, data_id):
        return get_annotation_value(
            group="longhorn.io",
            version="v1beta2",
            namespace="longhorn-system",
            plural="volumes",
            name=volume_name,
            annotation_key=f"{self.ANNOT_DATA_CHECKSUM}{data_id}",
        )

    @abstractmethod
    def attach(self, volume_name, node_name, disable_frontend):
        return NotImplemented

    @abstractmethod
    def detach(self, volume_name, node_name):
        return NotImplemented

    @abstractmethod
    def delete(self, volume_name):
        return NotImplemented

    @abstractmethod
    def wait_for_volume_state(self, volume_name, desired_state):
        return NotImplemented

    @abstractmethod
    def wait_for_volume_migration_ready(self, volume_name):
        return NotImplemented

    @abstractmethod
    def wait_for_volume_migration_completed(self, volume_name, node_name):
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

    # @abstractmethod
    # def cleanup(self, volume_names):
    #     return NotImplemented
