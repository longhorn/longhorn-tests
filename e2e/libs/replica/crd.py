from utility.utility import logging
from replica.base import Base
from replica.rest import Rest
from utils.common_utils import k8s_cr_api

class CRD(Base):
    def __init__(self, node_exec):
        self.cr_api = k8s_cr_api()
        self.node_exec = node_exec

    def get_replica(self, volume_name, node_name):
        label_selector = []
        if volume_name != "":
            label_selector.append(f"longhornvolume={volume_name}")
        if node_name != "":
            label_selector.append(f"longhornnode={node_name}")

        replicas = self.cr_api.list_namespaced_custom_object(
            group="longhorn.io",
            version="v1beta2",
            namespace="longhorn-system",
            plural="replicas",
            label_selector=",".join(label_selector)
        )
        return replicas

    def delete_replica(self, volume_name, node_name):
        if volume_name == "" or node_name == "":
            logging(f"Deleting all replicas")
        else:
            logging(
                f"Deleting volume {volume_name} on node {node_name} replicas")

        resp = self.get_replica(volume_name, node_name)
        assert resp != "", f"failed to get replicas"

        replicas = resp['items']
        if len(replicas) == 0:
            return

        for replica in replicas:
            replica_name = replica['metadata']['name']
            k8s_cr_api().delete_namespaced_custom_object(
                group="longhorn.io",
                version="v1beta2",
                namespace="longhorn-system",
                plural="replicas",
                name=replica_name
            )
        logging(f"Finished replicas deletion")

    def wait_for_replica_rebuilding_start(self, volume_name, node_name):
        Rest(self.node_exec).wait_for_replica_rebuilding_start(volume_name, node_name)

    def wait_for_replica_rebuilding_complete(self, volume_name, node_name):
        Rest(self.node_exec).wait_for_replica_rebuilding_complete(volume_name, node_name)
