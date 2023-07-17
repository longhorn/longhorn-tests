from abc import ABC, abstractmethod


class AbstractCloudProvider(ABC):
    @abstractmethod
    def get_all_node_instances(self):
        return NotImplemented

    @abstractmethod
    def get_node_instance(self, node_name):
        return NotImplemented

    @abstractmethod
    def power_off_node_instance(self, node_name):
        return NotImplemented

    @abstractmethod
    def power_on_node_instance(self, node_name=""):
        return NotImplemented
