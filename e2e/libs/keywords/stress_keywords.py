from robot.libraries.BuiltIn import BuiltIn

from node import Stress
from node.utility import list_node_names_by_role
from node.utility import list_node_names_by_volumes


class stress_keywords:

    def __init__(self):
        self.stress = Stress()

    def cleanup_stress_helper(self):
        self.stress.cleanup()

    def stress_node_cpu_by_role(self, role):
        self.stress.cpu(list_node_names_by_role(role))

    def stress_node_cpu_by_volumes(self, volume_names):
        self.stress.cpu(list_node_names_by_volumes(volume_names))

    def stress_node_memory_by_role(self, role):
        self.stress.memory(list_node_names_by_role(role))

    def stress_node_memory_by_volumes(self, volume_names):
        self.stress.memory(list_node_names_by_volumes(volume_names))
