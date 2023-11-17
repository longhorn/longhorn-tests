from abc import ABC, abstractmethod


class Base(ABC):

    @abstractmethod
    def get(self, volume_name):
        return NotImplemented

    @abstractmethod
    def create(self, volume_name, size, replica_count):
        return NotImplemented

    @abstractmethod
    def attach(self, volume_name, node_name):
        return NotImplemented

    @abstractmethod
    def delete(self, volume_name):
        return NotImplemented

    @abstractmethod
    def wait_for_volume_state(self, volume_name, desired_state):
        return NotImplemented

    @abstractmethod
    def get_endpoint(self, volume_name):
        return NotImplemented

    @abstractmethod
    def write_random_data(self, volume_name, size):
        return NotImplemented

    @abstractmethod
    def delete_replica(self, volume_name, node_name):
        return NotImplemented

    @abstractmethod
    def wait_for_replica_rebuilding_start(self, volume_name, node_name):
        return NotImplemented

    @abstractmethod
    def wait_for_replica_rebuilding_complete(self, volume_name, node_name):
        return NotImplemented

    @abstractmethod
    def check_data_checksum(self, volume_name, checksum):
        return NotImplemented

    @abstractmethod
    def cleanup(self, volume_names):
        return NotImplemented
