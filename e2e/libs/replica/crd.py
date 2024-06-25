from kubernetes import client

from replica.base import Base
from replica.rest import Rest

from utility.utility import logging


class CRD(Base):
    def __init__(self):
        self.obj_api = client.CustomObjectsApi()

    def get(self, volume_name, node_name):
        label_selector = []
        if volume_name != "":
            label_selector.append(f"longhornvolume={volume_name}")
        if node_name != "":
            label_selector.append(f"longhornnode={node_name}")

        replicas = self.obj_api.list_namespaced_custom_object(
            group="longhorn.io",
            version="v1beta2",
            namespace="longhorn-system",
            plural="replicas",
            label_selector=",".join(label_selector)
        )
        return replicas

    def delete(self, volume_name, node_name):
        if volume_name == "" or node_name == "":
            logging(f"Deleting all replicas")
        else:
            logging(
                f"Deleting volume {volume_name} on node {node_name} replicas")

        resp = self.get(volume_name, node_name)
        assert resp != "", f"failed to get replicas"

        replicas = resp['items']
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
