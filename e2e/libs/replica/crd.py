from kubernetes import client

from replica.base import Base
from replica.rest import Rest

from utility.utility import logging


class CRD(Base):
    def __init__(self):
        self.obj_api = client.CustomObjectsApi()

    def get(self, volume_name=None, node_name=None, disk_uuid=None):
        label_selector = []
        if volume_name:
            label_selector.append(f"longhornvolume={volume_name}")
        if node_name:
            label_selector.append(f"longhornnode={node_name}")
        if disk_uuid:
            label_selector.append(f"longhorndiskuuid={disk_uuid}")
        label_selector = ",".join(label_selector)
        logging(f"Getting replicas with labels {label_selector}")

        replicas = self.obj_api.list_namespaced_custom_object(
            group="longhorn.io",
            version="v1beta2",
            namespace="longhorn-system",
            plural="replicas",
            label_selector=label_selector
        )
        logging(f"Got replicas {replicas['items']}")
        return replicas["items"]

    def get_replica_names(self, volume_name, numberOfReplicas):
        logging(f"Getting volume {volume_name} replica names")
        replicas = self.get(volume_name)
        assert len(replicas) == numberOfReplicas, f"Expect volume {volume_name} has {numberOfReplicas} replicas, but there are {replicas}"
        replica_names = [ replica['metadata']['name'] for replica in replicas ]
        logging(f"Got volume {volume_name} replica names {replica_names}")
        return replica_names

    def delete(self, volume_name, node_name):
        if volume_name == "" or node_name == "":
            logging(f"Deleting all replicas")
        else:
            logging(
                f"Deleting volume {volume_name} on node {node_name} replicas")

        replicas = self.get(volume_name, node_name)
        if len(replicas) == 0:
            return

        for replica in replicas:
            replica_name = replica['metadata']['name']
            self.obj_api.delete_namespaced_custom_object(
                group="longhorn.io",
                version="v1beta2",
                namespace="longhorn-system",
                plural="replicas",
                name=replica_name
            )
        logging(f"Finished replicas deletion")

    def wait_for_rebuilding_start(self, volume_name, node_name):
        Rest().wait_for_rebuilding_start(volume_name, node_name)

    def wait_for_rebuilding_complete(self, volume_name, node_name):
        Rest().wait_for_rebuilding_complete(volume_name, node_name)

    def validate_replica_setting(self, volume_name, setting_name, value):
        replicas = self.get(volume_name)
        for replica in replicas:
            assert str(replica["spec"][setting_name]) == value, \
            f"Expected volume {volume_name} replica setting {setting_name} is {value}, but it's {str(replica['spec'][setting_name])}"
