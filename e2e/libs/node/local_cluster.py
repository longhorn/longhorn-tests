
class LocalCluster:

    _all_nodes = None

    def __init__(self, all_nodes) -> None:
        super().__init__()
        self._all_nodes = all_nodes

    def get_all_node_instances(self):
        raise Exception('NotImplemented')

    def get_node_instance(self, node_name):
        for instance in self._all_nodes:
            if instance['name'] == node_name:
                return instance

        raise Exception(f"can not find {node_name} instance")

    # Not supported
    def power_off_node_instance(self, node_name):
        raise Exception('NotImplemented')

    # Not supported
    def power_on_node_instance(self, node_name):
        raise Exception('NotImplemented')
