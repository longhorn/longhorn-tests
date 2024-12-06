import yaml
from abc import ABC, abstractmethod
from node.node import Node


class Base(ABC):

    def __init__(self):
        with open('/tmp/instance_mapping', 'r') as f:
            self.mapping = yaml.safe_load(f)
        self.node = Node()

    @abstractmethod
    def reboot_all_nodes(self, shut_down_time_in_sec):
        return NotImplemented

    @abstractmethod
    def reboot_node(self, node_name, shut_down_time_in_sec):
        return NotImplemented

    @abstractmethod
    def reboot_all_worker_nodes(self, shut_down_time_in_sec):
        return NotImplemented

    @abstractmethod
    def power_off_node(self, node_name, waiting):
        return NotImplemented

    @abstractmethod
    def power_on_node(self, node_name):
        return NotImplemented

