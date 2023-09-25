from abc import ABC, abstractmethod


class Base(ABC):

    @abstractmethod
    def get_engine(self, volume_name, node_name):
        return NotImplemented

    @abstractmethod
    def delete_engine(self, volume_name="", node_name=""):
        return NotImplemented
