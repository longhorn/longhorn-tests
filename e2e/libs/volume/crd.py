import time

from kubernetes import client

from utility.utility import get_retry_count_and_interval
from utility.utility import logging

from volume.base import Base
from volume.rest import Rest

from volume.constant import GIBIBYTE

class CRD(Base):

    def __init__(self, node_exec):
        self.obj_api = client.CustomObjectsApi()
        self.node_exec = node_exec
        self.retry_count, self.retry_interval = get_retry_count_and_interval()

    def get(self, volume_name):
        volume = self.obj_api.get_namespaced_custom_object(
            group="longhorn.io",
            version="v1beta2",
            namespace="longhorn-system",
            plural="volumes",
            name=volume_name
        )
        return volume

    def create(self, volume_name, size, replica_count):
        body = {
            "apiVersion": "longhorn.io/v1beta2",
            "kind": "Volume",
            "metadata": {"name": volume_name},
            "spec": {
                "frontend": "blockdev",
                "replicaAutoBalance": "ignored",
                "size": str(int(size) * GIBIBYTE),
                "numberOfReplicas": int(replica_count)
            }
        }
        self.obj_api.create_namespaced_custom_object(
            group="longhorn.io",
            version="v1beta2",
            namespace="longhorn-system",
            plural="volumes",
            body=body
        )
        self.wait_for_volume_state(volume_name, "detached")

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
        except Exception as e:
            # new CRD: volumeattachments was added since from 1.5.0
            # https://github.com/longhorn/longhorn/issues/3715
            if e.reason != "Not Found":
                Exception(f'exception for creating volumeattachments:', e)
        self.wait_for_volume_state(volume_name, "attached")

    def detach(self, volume_name):
        try:
            self.obj_api.patch_namespaced_custom_object(
                group="longhorn.io",
                version="v1beta2",
                namespace="longhorn-system",
                plural="volumeattachments",
                name=volume_name,
                body={
                    "spec": {
                        "attachmentTickets": None,
                    }
                }
            )
        except Exception as e:
            # new CRD: volumeattachments was added since from 1.5.0
            # https://github.com/longhorn/longhorn/issues/3715
            if e.reason != "Not Found":
                Exception(f'exception for patching volumeattachments:', e)

            self.obj_api.patch_namespaced_custom_object(
                group="longhorn.io",
                version="v1beta2",
                namespace="longhorn-system",
                plural="volumes",
                name=volume_name,
                body={
                        "spec": {
                            "nodeID": ""
                        }
                }
            )

        self.wait_for_volume_state(volume_name, "detached")

    def delete(self, volume_name):
        try:
            self.obj_api.delete_namespaced_custom_object(
                group="longhorn.io",
                version="v1beta2",
                namespace="longhorn-system",
                plural="volumes",
                name=volume_name
            )
            self.wait_for_volume_delete(volume_name)
        except Exception as e:
            logging(f"Deleting volume error: {e}")

    def wait_for_volume_delete(self, volume_name):
        for i in range(self.retry_count):
            try:
                self.obj_api.get_namespaced_custom_object(
                    group="longhorn.io",
                    version="v1beta2",
                    namespace="longhorn-system",
                    plural="volumes",
                    name=volume_name
                )
            except Exception as e:
                if e.reason == 'Not Found':
                    logging(f"Deleted volume {volume_name}")
                    return
                else:
                    logging(f"Waiting for volume deleting error: {e}")
            time.sleep(self.retry_interval)
        assert False, f"expect volume {volume_name} deleted but it still exists"

    def wait_for_volume_state(self, volume_name, desired_state):
        for i in range(self.retry_count):
            logging(f"Waiting for {volume_name} {desired_state} ({i}) ...")
            try:
                if self.get(volume_name)["status"]["state"] == desired_state:
                    break
            except Exception as e:
                logging(f"Getting volume {self.get(volume_name)} status error: {e}")
            time.sleep(self.retry_interval)
        assert self.get(volume_name)["status"]["state"] == desired_state

    def wait_for_volume_robustness(self, volume_name, desired_state):
        for i in range(self.retry_count):
            logging(f"Waiting for {volume_name} {desired_state} ({i}) ...")
            try:
                if self.get(volume_name)["status"]["robustness"] == desired_state:
                    break
            except Exception as e:
                logging(f"Getting volume {self.get(volume_name)} robustness error: {e}")
            time.sleep(self.retry_interval)
        assert self.get(volume_name)["status"]["robustness"] == desired_state

    def wait_for_volume_robustness_not(self, volume_name, not_desired_state):
        for i in range(self.retry_count):
            logging(f"Waiting for {volume_name} robustness not {not_desired_state} ({i}) ...")
            try:
                if self.get(volume_name)["status"]["robustness"] != not_desired_state:
                    break
            except Exception as e:
                logging(f"Getting volume {self.get(volume_name)} robustness error: {e}")
            time.sleep(self.retry_interval)
        assert self.get(volume_name)["status"]["robustness"] != not_desired_state

    def get_endpoint(self, volume_name):
        logging("Delegating the get_endpoint call to API because there is no CRD implementation")
        return Rest(self.node_exec).get_endpoint(volume_name)

    def write_random_data(self, volume_name, size):
        node_name = self.get(volume_name)["spec"]["nodeID"]
        endpoint = self.get_endpoint(volume_name)
        checksum = self.node_exec.issue_cmd(
            node_name,
            f"dd if=/dev/urandom of={endpoint} bs=1M count={size} status=none;\
              md5sum {endpoint} | awk \'{{print $1}}\'")
        return checksum

    def keep_writing_data(self, volume_name, size):
        node_name = self.get(volume_name)["spec"]["nodeID"]
        endpoint = self.get_endpoint(volume_name)
        logging(f"Keeping writing data to volume {volume_name}")
        res = self.node_exec.issue_cmd(
            node_name,
            f"while true; do dd if=/dev/urandom of={endpoint} bs=1M count={size} status=none; done > /dev/null 2> /dev/null &")
        logging(f"Created process to keep writing data to volume {volume_name}")

    def delete_replica(self, volume_name, node_name):
        replica_list = self.obj_api.list_namespaced_custom_object(
            group="longhorn.io",
            version="v1beta2",
            namespace="longhorn-system",
            plural="replicas",
            label_selector=f"longhornvolume={volume_name}\
                             ,longhornnode={node_name}"
        )
        logging(f"Deleting replica {replica_list['items'][0]['metadata']['name']}")
        self.obj_api.delete_namespaced_custom_object(
            group="longhorn.io",
            version="v1beta2",
            namespace="longhorn-system",
            plural="replicas",
            name=replica_list['items'][0]['metadata']['name']
        )

    def wait_for_replica_rebuilding_start(self, volume_name, node_name):
        logging("Delegating the wait_for_replica_rebuilding_start call to API because there is no CRD implementation")
        Rest(self.node_exec).wait_for_replica_rebuilding_start(volume_name, node_name)

    def wait_for_replica_rebuilding_complete(self, volume_name, node_name):
        logging("Delegating the wait_for_replica_rebuilding_complete call to API because there is no CRD implementation")
        Rest(self.node_exec).wait_for_replica_rebuilding_complete(
            volume_name,
            node_name
        )

    def check_data_checksum(self, volume_name, checksum):
        node_name = self.get(volume_name)["spec"]["nodeID"]
        endpoint = self.get_endpoint(volume_name)
        _checksum = self.node_exec.issue_cmd(
            node_name,
            f"md5sum {endpoint} | awk \'{{print $1}}\'")
        logging(f"Got {endpoint} checksum = {_checksum},\
                expected checksum = {checksum}")
        assert _checksum == checksum

    def cleanup(self, volume_names):
        for volume_name in volume_names:
            logging(f"Deleting volume {volume_name}")
            self.delete(volume_name)