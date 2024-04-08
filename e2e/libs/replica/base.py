from abc import ABC, abstractmethod


class Base(ABC):

    @abstractmethod
    def get(self, volume_name, node_name):
        return NotImplemented

    @abstractmethod
    def delete(self, volume_name, node_name):
        return NotImplemented

    @abstractmethod
    def wait_for_rebuilding_start(self, volume_name, node_name):
        return NotImplemented

    @abstractmethod
    def wait_for_rebuilding_complete(self, volume_name, node_name):
        return NotImplemented
