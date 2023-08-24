import os
import time
import warnings

from volume.base import Base
from volume.rest import Rest
from kubernetes import client

Ki = 2**10
Mi = 2**20
Gi = 2**30

retry_count = 200
retry_interval = 1


class CRD(Base):

    def __init__(self, node_exec):
        self.obj_api = client.CustomObjectsApi()
        self.node_exec = node_exec

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
                "size": str(int(size) * Gi),
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

    def wait_for_volume_state(self, volume_name, desired_state):
        for i in range(retry_count):
            try:
                if self.get(volume_name)["status"]["state"] == desired_state:
                    break
            except Exception as e:
                print(f"get volume {self.get(volume_name)} status error: {e}")
            time.sleep(retry_interval)
        assert self.get(volume_name)["status"]["state"] == desired_state

    def get_endpoint(self, volume_name):
        warnings.warn("no endpoint in volume cr, get it from rest api")
        return Rest(self.node_exec).get_endpoint(volume_name)

    def write_random_data(self, volume_name, size):
        node_name = self.get(volume_name)["spec"]["nodeID"]
        endpoint = self.get_endpoint(volume_name)
        checksum = self.node_exec.issue_cmd(
            node_name,
            f"dd if=/dev/urandom of={endpoint} bs=1M count={size} status=none;\
              md5sum {endpoint} | awk \'{{print $1}}\'")
        return checksum

    def delete_replica(self, volume_name, node_name):
        replica_list = self.obj_api.list_namespaced_custom_object(
            group="longhorn.io",
            version="v1beta2",
            namespace="longhorn-system",
            plural="replicas",
            label_selector=f"longhornvolume={volume_name}\
                             ,longhornnode={node_name}"
        )
        print(f"delete replica {replica_list['items'][0]['metadata']['name']}")
        self.obj_api.delete_namespaced_custom_object(
            group="longhorn.io",
            version="v1beta2",
            namespace="longhorn-system",
            plural="replicas",
            name=replica_list['items'][0]['metadata']['name']
        )

    def wait_for_replica_rebuilding_start(self, volume_name, node_name):
        warnings.warn("no rebuild status in volume cr, get it from rest api")
        Rest(self.node_exec).wait_for_replica_rebuilding_start(volume_name, node_name)

    def wait_for_replica_rebuilding_complete(self, volume_name, node_name):
        warnings.warn("no rebuild status in volume cr, get it from rest api")
        Rest(self.node_exec).wait_for_replica_rebuilding_complete(
            volume_name,
            node_name
        )

    def check_data(self, volume_name, checksum):
        node_name = self.get(volume_name)["spec"]["nodeID"]
        endpoint = self.get_endpoint(volume_name)
        _checksum = self.node_exec.issue_cmd(
            node_name,
            f"md5sum {endpoint} | awk \'{{print $1}}\'")
        print(f"get {endpoint} checksum = {_checksum},\
                expected checksum = {checksum}")
        assert _checksum == checksum