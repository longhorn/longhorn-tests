from robot.libraries.BuiltIn import BuiltIn
from k8s.k8s import restart_kubelet
from k8s.k8s import delete_node
from k8s.k8s import drain_node, force_drain_node
from k8s.k8s import cordon_node, uncordon_node


class k8s_keywords:

    def restart_kubelet(self, node_name, stop_time_in_sec):
        restart_kubelet(node_name, int(stop_time_in_sec))

    def delete_volume_node(self, volume_name):
        volume_keywords = BuiltIn().get_library_instance('volume_keywords')
        volume_node = volume_keywords.get_volume_node(volume_name)
        delete_node(volume_node)
        return volume_node

    def delete_replica_node(self, volume_name):
        volume_keywords = BuiltIn().get_library_instance('volume_keywords')
        replica_node = volume_keywords.get_replica_node(volume_name)
        delete_node(replica_node)
        return replica_node

    def drain_node(self, node_name):
        drain_node(node_name)

    def force_drain_node(self, node_name):
        force_drain_node(node_name)

    def uncordon_node(self, node_name):
        uncordon_node(node_name)
