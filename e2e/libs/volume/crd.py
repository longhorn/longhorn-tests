import time
import logging

from utils.common_utils import k8s_cr_api
from volume.base import Base
from volume.rest import Rest
from kubernetes import client
from kubernetes.client.rest import ApiException

Ki = 2**10
Mi = 2**20
Gi = 2**30

retry_count = 200
retry_interval = 1


class CRD(Base):

    def __init__(self, node_exec):
        self.node_exec = node_exec

    def create(self, volume_name, size, replica_count, volume_type):
        logging.info(
            f"creating {size} Gi {volume_type} volume with {replica_count} replicas")

        volume_body = {
            "apiVersion": "longhorn.io/v1beta2",
            "kind": "Volume",
            "metadata": {"name": volume_name},
            "spec": {
                "frontend": "blockdev",
                "replicaAutoBalance": "ignored",
                "size": str(int(size) * Gi),
                "numberOfReplicas": int(replica_count),
                "accessMode": volume_type.lower()
            }
        }

        k8s_cr_api().create_namespaced_custom_object(
            group="longhorn.io",
            version="v1beta2",
            namespace="longhorn-system",
            plural="volumes",
            body=volume_body
        )

    def create_with_manifest(self, manifest):
        k8s_cr_api().create_namespaced_custom_object(
            group="longhorn.io",
            version="v1beta2",
            namespace="longhorn-system",
            plural="volumes",
            body=manifest
        )

    def get(self, volume_name=""):
        volume = k8s_cr_api().get_namespaced_custom_object(
            group="longhorn.io",
            version="v1beta2",
            namespace="longhorn-system",
            plural="volumes",
            name=volume_name
        )
        return volume

    def delete(self, volume_name):
        if volume_name == "":
            logging.info("deleting all volumes")
        else:
            logging.info(f"deleting the volume {volume_name}")

        resp = self.get(volume_name)
        assert resp != "", "failed to get the volume"

        volume_list = resp['items']
        if len(volume_list) == 0:
            logging.warning("cannot find the volume")
            return

        for volume in volume_list:
            volume_name = volume['metadata']['name']
            k8s_cr_api().delete_namespaced_custom_object(
                group="longhorn.io",
                version="v1beta2",
                namespace="longhorn-system",
                plural="volumes",
                name=volume_name
            )
        logging.info("finished deleting volume")

    def attach(self, volume_name, node_name):
        k8s_cr_api().patch_namespaced_custom_object(
            group="longhorn.io",
            version="v1beta2",
            namespace="longhorn-system",
            plural="volumes",
            name=volume_name,
            body={
                    "spec": {
                        "nodeID": node_name
                    }
            }
        )

        try:
            k8s_cr_api().patch_namespaced_custom_object(
                group="longhorn.io",
                version="v1beta2",
                namespace="longhorn-system",
                plural="volumeattachments",
                name=volume_name,
                body={
                        "spec": {
                            "attachmentTickets": {
                                "": {
                                    "generation": 0,
                                    "id": "",
                                    "nodeID": node_name,
                                    "parameters": {
                                        "disableFrontend": "false",
                                        "lastAttachedBy": ""
                                    },
                                    "type": "longhorn-api"
                                }
                            }
                        }
                }
            )
        except ApiException as e:
            # new CRD: volumeattachments was added since from 1.5.0
            # https://github.com/longhorn/longhorn/issues/3715
            if e.reason != "Not Found":
                Exception(f'exception for creating volumeattachments:', e)

        self.wait_for_volume_state(volume_name, "attached")

    def wait_for_volume_state(self, volume_name, desired_state):
        logging.info(
            f"waiting volume {volume_name} state becomes {desired_state}")
        for i in range(retry_count):
            volume_state = self.get(volume_name)["status"]["state"]
            if volume_state == desired_state:
                break
            time.sleep(retry_interval)
        assert self.get(volume_name)["status"]["state"] == desired_state

    def get_volume_state(self, volume_name):
        logging.info(f"getting volume {volume_name} state")
        return self.get(volume_name)["status"]["robustness"]

    def get_endpoint(self, volume_name):
        logging.info(f"getting volume {volume_name} endpoint")
        return Rest(self.node_exec).get_endpoint(volume_name)

    def write_random_data(self, volume_name, size):
        logging.info(
            f"writing {size} Mb data into volume {volume_name} mount point")

        node_name = self.get(volume_name)["spec"]["nodeID"]
        endpoint = self.get_endpoint(volume_name)

        checksum = self.node_exec.issue_cmd(
            node_name,
            f"dd if=/dev/urandom of={endpoint} bs=2M count={size} status=none;\
              md5sum {endpoint} | awk \'{{print $1}}\'")
        return checksum

    def check_data(self, volume_name, checksum):
        node_name = self.get(volume_name)["spec"]["nodeID"]
        endpoint = self.get_endpoint(volume_name)
        _checksum = self.node_exec.issue_cmd(
            node_name,
            f"md5sum {endpoint} | awk \'{{print $1}}\'")
        if _checksum != checksum:
            Exception(f"data was changed: {_checksum}/{checksum}")
