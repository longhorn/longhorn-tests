from node import Node
from node import Stress

from volume import Volume

from utility.constant import LABEL_TEST
from utility.constant import LABEL_TEST_VALUE
from utility.utility import logging


class stress_keywords:

    def __init__(self):
        self.node = Node()
        self.stress = Stress()
        self.volume = Volume()

    def cleanup_stress_helper(self):
        logging(f'Cleaning up stress helper')
        self.stress.cleanup()

    def stress_node_cpu_by_role(self, role):
        logging(f'Stressing node CPU for {role} nodes')
        self.stress.cpu(self.node.list_node_names_by_role(role))

    def stress_node_cpu_by_volume(self, volume_name):
        logging(f'Stressing node CPU for volume {volume_name}')
        self.stress_node_cpu_by_volumes([volume_name])

    def stress_node_cpu_by_volumes(self, volume_names):
        logging(f'Stressing node CPU for volumes {volume_names}')
        self.stress.cpu(self.node.list_node_names_by_volumes(volume_names))

    def stress_node_cpu_of_all_volumes(self):
        volume_names = self.volume.list_names(label_selector=f"{LABEL_TEST}={LABEL_TEST_VALUE}")

        logging(f'Stressing node CPU for all volumes {volume_names}')
        self.stress_node_cpu_by_volumes(volume_names)

    def stress_node_memory_by_role(self, role):
        logging(f'Stressing node memory for {role} nodes')
        self.stress.memory(self.node.list_node_names_by_role(role))

    def stress_node_memory_by_volume(self, volume_name):
        logging(f'Stressing node memory for volume {volume_name}')
        self.stress_node_memory_by_volumes([volume_name])

    def stress_node_memory_by_volumes(self, volume_names):
        logging(f'Stressing node memory for volumes {volume_names}')
        self.stress.memory(self.node.list_node_names_by_volumes(volume_names))

    def stress_node_memory_of_all_volumes(self):
        volume_names = self.volume.list_names(label_selector=f"{LABEL_TEST}={LABEL_TEST_VALUE}")

        logging(f'Stressing node memory for all volumes {volume_names}')
        self.stress_node_memory_by_volumes(volume_names)
