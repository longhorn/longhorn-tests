import time
import logging

from utility import Utility
from volume.abstract_volume import AbstractVolume
from volume.rest_volume import RestVolume
from kubernetes import client
from kubernetes.client.rest import ApiException

Ki = 2**10
Mi = 2**20
Gi = 2**30

retry_count = 200
retry_interval = 1


class CRDVolume(AbstractVolume):

    def __init__(self, node_exec):
        self.obj_api = client.CustomObjectsApi()
        self.node_exec = node_exec

    def get(self, volume_name=""):
        volume = self.obj_api.get_namespaced_custom_object(
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
        if resp == "":
            raise Exception("failed to get the volume")

        volume_list = resp['items']
        if len(volume_list) == 0:
            logging.warning("cannot find the volume")
            return

        for volume in volume_list:
            volume_name = volume['metadata']['name']
            logging.debug(f"deleting volume {volume_name}")
            self.obj_api.delete_namespaced_custom_object(
                group="longhorn.io",
                version="v1beta2",
                namespace="longhorn-system",
                plural="volumes",
                name=volume_name
            )
        logging.info("finished deleting volume")

    def create(self, volume_name, size, replica_count, volume_type):
        logging.info(f"creating {size} Gi {volume_type} volume with {replica_count} replicas")

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
        logging.debug(f"volume creation body: {volume_body}")

        api_response = self.obj_api.create_namespaced_custom_object(
            group="longhorn.io",
            version="v1beta2",
            namespace="longhorn-system",
            plural="volumes",
            body=volume_body
        )
        logging.debug(f"response of volume creation {api_response}")

    def attach(self, volume_name, node_name):
        self.obj_api.patch_namespaced_custom_object(
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
            self.obj_api.patch_namespaced_custom_object(
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
        logging.info(f"waiting volume {volume_name} state becomes {desired_state}")
        for i in range(retry_count):
            volume_state = self.get(volume_name)["status"]["state"]
            logging.debug(f"volume state: {volume_state}")
            if volume_state == desired_state:
                break
            time.sleep(retry_interval)
        assert self.get(volume_name)["status"]["state"] == desired_state

    def get_volume_state(self, volume_name):
        logging.info(f"getting volume {volume_name} state")
        return self.get(volume_name)["status"]["robustness"]

    def get_endpoint(self, volume_name):
        logging.info(f"getting volume {volume_name} endpoint")
        return RestVolume(self.node_exec).get_endpoint(volume_name)

    def write_random_data(self, volume_name, size):
        logging.info(f"writing {size} Mb data into volume {volume_name} mount point")

        node_name = self.get(volume_name)["spec"]["nodeID"]
        endpoint = self.get_endpoint(volume_name)

        logging.debug(f"starting write data into {endpoint} on node {node_name}")
        checksum = self.node_exec.issue_cmd(
            node_name,
            f"dd if=/dev/urandom of={endpoint} bs=2M count={size} status=none;\
              md5sum {endpoint} | awk \'{{print $1}}\'")
        logging.debug(f'finishing write data')
        return checksum

    def get_replica(self, volume_name, node_name):
        label_selector=[]
        if volume_name!="":
            label_selector.append(f"longhornvolume={volume_name}")
        if node_name!="":
            label_selector.append(f"longhornnode={node_name}")

        str_label_selector=",".join(label_selector)
        logging.debug(f'str_label_selector={str_label_selector}')
        replicas =  self.obj_api.list_namespaced_custom_object(
            group="longhorn.io",
            version="v1beta2",
            namespace="longhorn-system",
            plural="replicas",
            label_selector=",".join(label_selector)
        )
        return replicas

    def delete_replica(self, volume_name, node_name):
        if volume_name == "" or node_name == "":
            logging.info(f"deleting all replicas")
        else:
            logging.info(f"deleting the volume {volume_name} on node {node_name} replicas")

        resp = self.get_replica(volume_name, node_name)
        if resp == "":
            raise Exception(f"failed to get replicas")

        replicas = resp['items']
        if len(replicas) == 0:
            logging.debug(f"cannot find any replicas")
            return

        for replica in replicas:
            replica_name = replica['metadata']['name']
            logging.debug(f"delete replica {replica_name}")
            api_response = self.obj_api.delete_namespaced_custom_object(
                                group="longhorn.io",
                                version="v1beta2",
                                namespace="longhorn-system",
                                plural="replicas",
                                name=replica_name
                            )
            logging.debug(f"response of replica deletion: {api_response}")
        logging.info(f"finished replicas deletion")

    def get_engine(self, volume_name, node_name):
        if volume_name == "" or node_name == "":
            logging.info("getting all engines")
        else:
            logging.info(f"getting the volume {volume_name} on node {node_name} engine")

        label_selector=[]
        if volume_name!="":
            label_selector.append(f"longhornvolume={volume_name}")
        if node_name!="":
            label_selector.append(f"longhornnode={node_name}")

        str_label_selector=",".join(label_selector)
        logging.debug(f'label_selector={str_label_selector}')
        api_response =  self.obj_api.list_namespaced_custom_object(
            group="longhorn.io",
            version="v1beta2",
            namespace="longhorn-system",
            plural="engines",
            label_selector=",".join(label_selector)
        )
        logging.debug(f"response of getting engine: {api_response}")
        return api_response

    def delete_engine(self, volume_name, node_name):
        if volume_name == "" or node_name == "":
            logging.info("deleting all engines")
        else:
            logging.info(f"delete the volume {volume_name} on node {node_name} engine")

        resp = self.get_engine(volume_name, node_name)
        if resp == "":
            raise Exception("failed to get engines")

        engines = resp['items']
        if len(engines) == 0:
            logging.warning("cannot find engines")
            return

        for engine in engines:
            engine_name = engine['metadata']['name']
            logging.debug(f"deleting engine {engine_name}")
            self.obj_api.delete_namespaced_custom_object(
                group="longhorn.io",
                version="v1beta2",
                namespace="longhorn-system",
                plural="engines",
                name=engine_name
            )
        logging.info("finished delete engines")

    def wait_for_replica_rebuilding_start(self, volume_name, node_name):
        RestVolume(self.node_exec).wait_for_replica_rebuilding_start(volume_name, node_name)

    def wait_for_replica_rebuilding_complete(self, volume_name, node_name):
        RestVolume(self.node_exec).wait_for_replica_rebuilding_complete(volume_name, node_name)

    def check_data(self, volume_name, checksum):
        node_name = self.get(volume_name)["spec"]["nodeID"]
        endpoint = self.get_endpoint(volume_name)
        _checksum = self.node_exec.issue_cmd(
            node_name,
            f"md5sum {endpoint} | awk \'{{print $1}}\'")
        print(f"get {endpoint} checksum = {_checksum},\
                expected checksum = {checksum}")
        if _checksum != checksum:
            Exception(f"data was changed: {_checksum}/{checksum}")
