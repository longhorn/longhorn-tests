import time
from kubernetes.client.rest import ApiException
from kubernetes import client

from engine import Engine

from utility.constant import LABEL_TEST
from utility.constant import LABEL_TEST_VALUE
from utility.utility import get_retry_count_and_interval
from utility.utility import logging

from volume.base import Base
from volume.constant import GIBIBYTE
from volume.rest import Rest


class CRD(Base):

    def __init__(self, node_exec):
        self.obj_api = client.CustomObjectsApi()
        self.node_exec = node_exec
        self.retry_count, self.retry_interval = get_retry_count_and_interval()

    def create(self, volume_name, size, replica_count, frontend="blockdev"):
        size = str(int(size) * GIBIBYTE)
        body = {
            "apiVersion": "longhorn.io/v1beta2",
            "kind": "Volume",
            "metadata": {
                "name": volume_name,
                "labels": {
                    LABEL_TEST: LABEL_TEST_VALUE
                }
            },
            "spec": {
                "frontend": frontend,
                "replicaAutoBalance": "ignored",
                "size": size,
                "numberOfReplicas": int(replica_count)
            }
        }
        try:
            self.obj_api.create_namespaced_custom_object(
                group="longhorn.io",
                version="v1beta2",
                namespace="longhorn-system",
                plural="volumes",
                body=body
            )
            self.wait_for_volume_state(volume_name, "detached")
            volume = self.get(volume_name)
            assert volume['metadata']['name'] == volume_name, f"expect volume name is {volume_name}, but it's {volume['metadata']['name']}"
            assert volume['spec']['size'] == size, f"expect volume size is {size}, but it's {volume['spec']['size']}"
            assert volume['spec']['numberOfReplicas'] == int(replica_count), f"expect volume numberOfReplicas is {replica_count}, but it's {volume['spec']['numberOfReplicas']}"
            assert volume['spec']['frontend'] == frontend, f"expect volume frontend is {frontend}, but it's {volume['spec']['frontend']}"
            assert volume['status']['restoreRequired'] is False, f"expect volume restoreRequired is False, but it's {volume['status']['restoreRequired']}"
            #assert volume['backingImage'] == backing_image, f"expect volume backingImage is {backing_image}, but it's {volume['backingImage']}"
        except ApiException as e:
            logging(e)

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

    def get(self, volume_name):
        return self.obj_api.get_namespaced_custom_object(
            group="longhorn.io",
            version="v1beta2",
            namespace="longhorn-system",
            plural="volumes",
            name=volume_name
        )

    def list(self, label_selector=None):
        return self.obj_api.list_namespaced_custom_object(
            group="longhorn.io",
            version="v1beta2",
            namespace="longhorn-system",
            plural="volumes",
            label_selector=label_selector
        )

    def set_annotation(self, volume_name, annotation_key, annotation_value):
        # retry conflict error
        for i in range(self.retry_count):
            try:
                volume = self.get(volume_name)
                annotations = volume['metadata'].get('annotations', {})
                annotations[annotation_key] = annotation_value
                volume['metadata']['annotations'] = annotations
                self.obj_api.replace_namespaced_custom_object(
                    group="longhorn.io",
                    version="v1beta2",
                    namespace="longhorn-system",
                    plural="volumes",
                    name=volume_name,
                    body=volume
                )
                break
            except Exception as e:
                if e.status == 409:
                    logging(f"Conflict error: {e.body}, retry ({i}) ...")
                else:
                    raise e
            time.sleep(self.retry_interval)

    def get_annotation_value(self, volume_name, annotation_key):
        volume = self.get(volume_name)
        return volume['metadata']['annotations'].get(annotation_key)

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
        volume = None
        for i in range(self.retry_count):
            logging(f"Waiting for {volume_name} {desired_state} ({i}) ...")
            try:
                volume = self.get(volume_name)
                if volume["status"]["state"] == desired_state:
                    break
            except Exception as e:
                logging(f"Getting volume {volume} status error: {e}")
            time.sleep(self.retry_interval)
        assert volume["status"]["state"] == desired_state

    def wait_for_volume_robustness(self, volume_name, desired_state):
        volume = None
        for i in range(self.retry_count):
            logging(f"Waiting for {volume_name} {desired_state} ({i}) ...")
            try:
                volume = self.get(volume_name)
                if volume["status"]["robustness"] == desired_state:
                    break
            except Exception as e:
                logging(f"Getting volume {volume} robustness error: {e}")
            time.sleep(self.retry_interval)
        assert volume["status"]["robustness"] == desired_state

    def wait_for_volume_robustness_not(self, volume_name, not_desired_state):
        volume = None
        for i in range(self.retry_count):
            logging(f"Waiting for {volume_name} robustness not {not_desired_state} ({i}) ...")
            try:
                volume = self.get(volume_name)
                if volume["status"]["robustness"] != not_desired_state:
                    break
            except Exception as e:
                logging(f"Getting volume {volume} robustness error: {e}")
            time.sleep(self.retry_interval)
        assert volume["status"]["robustness"] != not_desired_state

    def wait_for_volume_expand_to_size(self, volume_name, expected_size):
        engine = None
        engine_current_size = 0
        engine_expected_size = int(expected_size)
        engine_operation = Engine()
        for i in range(self.retry_count):
            engine = engine_operation.get_engine_by_volume(self.get(volume_name))
            engine_current_size = int(engine['status']['currentSize'])
            if engine_current_size == engine_expected_size:
                break

            logging(f"Waiting for volume engine expand from {engine_current_size} to {expected_size} ({i}) ...")

            time.sleep(self.retry_interval)

        assert engine is not None
        assert engine_current_size == engine_expected_size

    def get_endpoint(self, volume_name):
        logging("Delegating the get_endpoint call to API because there is no CRD implementation")
        return Rest(self.node_exec).get_endpoint(volume_name)

    def write_random_data(self, volume_name, size):
        node_name = self.get(volume_name)["spec"]["nodeID"]
        endpoint = self.get_endpoint(volume_name)

        dd_command = f"dd if=/dev/urandom of={endpoint} bs=1M count={size} status=none"
        dd_command_output = self.node_exec.issue_cmd(node_name, dd_command).strip()

        try:
            assert dd_command_output == ""
        except AssertionError:
            logging(f"Failed to write random data to volume {volume_name}. \n"
                    f"Command: {dd_command}\n"
                    f"Output: {dd_command_output}")

            logging(f"Pausing the test for {self.retry_count} seconds ...")
            time.sleep(self.retry_count)

        assert dd_command_output == "", \
            f"Failed to write random data to volume {volume_name}.\n" \
            f"Command: {dd_command}\n" \
            f"Output: {dd_command_output}"
        return self.node_exec.issue_cmd(node_name, f"md5sum {endpoint} | awk \'{{print $1}}\'")

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
        actual_checksum = self.node_exec.issue_cmd(
            node_name,
            f"md5sum {endpoint} | awk \'{{print $1}}\'")
        assert actual_checksum == checksum

    def validate_volume_replicas_anti_affinity(self, volume_name):
        replica_list = self.obj_api.list_namespaced_custom_object(
            group="longhorn.io",
            version="v1beta2",
            namespace="longhorn-system",
            plural="replicas",
            label_selector=f"longhornvolume={volume_name}"
        )['items']
        node_set = set()
        for replica in replica_list:
            node_set.add(replica['status']['ownerID'])
        assert len(replica_list) == len(node_set), f"unexpected replicas on the same node: {replica_list}"
