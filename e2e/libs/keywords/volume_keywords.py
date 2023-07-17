import logging

from common_keywords import common_keywords
from node import Nodes
from utils import common_utils

class volume_keywords:

    def __init__(self):
        self.volume = common_keywords.volume_instance
        self.node_exec = common_keywords.node_exec_instance

    def create_volume(self, size, replica_count, volume_type='RWO'):
        volume_name = common_utils.generate_volume_name()
        self.volume.create(volume_name, size, replica_count, volume_type)
        return volume_name

    def create_volume_manifest(self):
        volume_name = common_utils.generate_volume_name()
        manifest = {
            "apiVersion": "longhorn.io/v1beta2",
            "kind": "Volume",
            "metadata": {"name": volume_name},
            "spec": {
                "frontend": "blockdev",
                "replicaAutoBalance": "ignored",
            }
        }
        return volume_name, manifest

    def update_manifest_field(self, manifest, field):
        dict_field = eval(field)
        for key in dict_field.keys():
            if key in manifest.keys():
                for key2 in dict_field[key]:
                    manifest[key][key2] = dict_field[key][key2]
            else:
                manifest.update(dict_field)
        return manifest

    def create_volume_using_manifest(self,manifest):
        return self.volume.create_with_manifest(manifest)

    def attach_volume(self, volume_name, node_index=0):
        node_name = Nodes.get_name_by_index(int(node_index))
        logging.info(
            f'attaching the volume {volume_name} to the node {node_name}')

        self.volume.attach(volume_name, node_name)
        return node_name

    def get_non_volume_attached_node(self, attached_node_name):
        logging.info('getting node without volume attached')
        nodes = Nodes.all_nodes
        for node in nodes:
            node_name = node['name']
            if node_name != attached_node_name:
                logging.info(f' volume attached node:{node_name}')
                return node_name
        logging.info('cannot find the node without volume attached')

    def write_volume_random_data(self, volume_name, size_in_mb):
        logging.info(
            f'writing {size_in_mb} mb data into volume {volume_name} mount point')
        return self.volume.write_random_data(volume_name, size_in_mb)

    def get_volume_end_point(self, volume_name):
        logging.info(f'gettting volume {volume_name} end point')
        return self.volume.get_endpoint(volume_name)

    def check_data(self, volume_name, checksum):
        logging.info(f"checking volume {volume_name} data with checksum {checksum}")
        self.volume.check_data(volume_name, checksum)

    def get_volume_state(self, volume_name):
        logging.info(f"getting the volume {volume_name} state")
        return self.volume.get_volume_state(volume_name)
