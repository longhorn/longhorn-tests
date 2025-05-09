import time

from kubernetes import client
from kubernetes.client.rest import ApiException

from engine import Engine

from node_exec import NodeExec

from utility.constant import LABEL_TEST
from utility.constant import LABEL_TEST_VALUE
from utility.utility import get_retry_count_and_interval
from utility.utility import logging
from utility.utility import get_cr

from volume.base import Base
from volume.constant import GIBIBYTE, MEBIBYTE
from volume.rest import Rest


class CRD(Base):

    def __init__(self):
        self.core_api = client.CoreV1Api()
        self.obj_api = client.CustomObjectsApi()
        self.retry_count, self.retry_interval = get_retry_count_and_interval()
        self.engine = Engine()

    def create(self, volume_name, size, numberOfReplicas, frontend, migratable, dataLocality, accessMode, dataEngine, backingImage, Standby, fromBackup, encrypted):
        size_suffix = size[-2:]
        size_number = size[:-2]
        size_unit = MEBIBYTE if size_suffix == "Mi" else GIBIBYTE
        size = str(int(size_number) * size_unit)
        accessMode = accessMode.lower()
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
                "encrypted": encrypted,
                "frontend": frontend,
                "replicaAutoBalance": "ignored",
                "size": size,
                "numberOfReplicas": int(numberOfReplicas),
                "migratable": migratable,
                "dataLocality": dataLocality,
                "accessMode": accessMode,
                "dataEngine": dataEngine,
                "backingImage": backingImage,
                "Standby": Standby,
                "fromBackup": fromBackup,
                # disable revision counter by default from v1.7.0
                "revisionCounterDisabled": True
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
            if fromBackup or Standby:
                self.wait_for_volume_state(volume_name, "attached")
                self.wait_for_restore_required_status(volume_name, True)
            else:
                self.wait_for_volume_state(volume_name, "detached")
                self.wait_for_restore_required_status(volume_name, False)
            volume = self.get(volume_name)
            assert volume['metadata']['name'] == volume_name, f"expect volume name is {volume_name}, but it's {volume['metadata']['name']}"
            if not Standby:
                assert volume['spec']['size'] == size, f"expect volume size is {size}, but it's {volume['spec']['size']}"
            assert volume['spec']['numberOfReplicas'] == int(numberOfReplicas), f"expect volume numberOfReplicas is {numberOfReplicas}, but it's {volume['spec']['numberOfReplicas']}"
            assert volume['spec']['frontend'] == frontend, f"expect volume frontend is {frontend}, but it's {volume['spec']['frontend']}"
            assert volume['spec']['migratable'] == migratable, f"expect volume migratable is {migratable}, but it's {volume['spec']['migratable']}"
            assert volume['spec']['dataLocality'] == dataLocality, f"expect volume dataLocality is {dataLocality}, but it's {volume['spec']['dataLocality']}"
            assert volume['spec']['accessMode'] == accessMode, f"expect volume accessMode is {accessMode}, but it's {volume['spec']['accessMode']}"
            assert volume['spec']['backingImage'] == backingImage, f"expect volume backingImage is {backingImage}, but it's {volume['spec']['backingImage']}"
            assert volume['spec']['Standby'] == Standby, f"expect volume Standby is {Standby}, but it's {volume['spec']['Standby']}"
            assert volume['spec']['fromBackup'] == fromBackup, f"expect volume fromBackup is {fromBackup}, but it's {volume['spec']['fromBackup']}"
            assert volume['spec']['encrypted'] == encrypted, f"expect volume encrypted is {encrypted}, but it's {volume['spec']['encrypted']}"
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
            self.wait_for_volume_deleted(volume_name)
        except Exception as e:
            logging(f"Deleting volume error: {e}")

    def attach(self, volume_name, node_name, disable_frontend):

        migratable = self.get(volume_name)['spec']['migratable']
        type = "longhorn-api" if not migratable else "csi-attacher"

        try:
            body = get_cr(
                group="longhorn.io",
                version="v1beta2",
                namespace="longhorn-system",
                plural="volumeattachments",
                name=volume_name
            )
            body['spec']['attachmentTickets'][node_name] = {
                "id": node_name,
                "nodeID": node_name,
                "parameters": {
                    "disableFrontend": "true" if disable_frontend else "false",
                    "lastAttachedBy": ""
                },
                    "type": type
            }

            self.obj_api.patch_namespaced_custom_object(
                group="longhorn.io",
                version="v1beta2",
                namespace="longhorn-system",
                plural="volumeattachments",
                name=volume_name,
                body=body
            )
        except Exception as e:
            # new CRD: volumeattachments was added since from 1.5.0
            # https://github.com/longhorn/longhorn/issues/3715
            if e.reason != "Not Found":
                Exception(f'exception for creating volumeattachments:', e)
        self.wait_for_volume_state(volume_name, "attached")
        self.wait_for_volume_status(volume_name, "frontendDisabled", disable_frontend)

    def is_attached_to(self, volume_name, node_name):
        return Rest().is_attached_to(volume_name, node_name)

    def detach(self, volume_name, node_name):
        try:
            body = get_cr(
                group="longhorn.io",
                version="v1beta2",
                namespace="longhorn-system",
                plural="volumeattachments",
                name=volume_name
            )
            del body['spec']['attachmentTickets'][node_name]

            self.obj_api.replace_namespaced_custom_object(
                group="longhorn.io",
                version="v1beta2",
                namespace="longhorn-system",
                plural="volumeattachments",
                name=volume_name,
                body=body
            )
        except Exception as e:
            # new CRD: volumeattachments was added since from 1.5.0
            # https://github.com/longhorn/longhorn/issues/3715
            if e.reason != "Not Found":
                Exception(f'exception for patching volumeattachments:', e)

    def get(self, volume_name):
        return self.obj_api.get_namespaced_custom_object(
            group="longhorn.io",
            version="v1beta2",
            namespace="longhorn-system",
            plural="volumes",
            name=volume_name
        )

    def list(self, label_selector=None, dataEngine=None):
        items = self.obj_api.list_namespaced_custom_object(
            group="longhorn.io",
            version="v1beta2",
            namespace="longhorn-system",
            plural="volumes",
            label_selector=label_selector
        )["items"]

        if not dataEngine:
            return items
        else:
            return [item for item in items if item['spec']['dataEngine'] == dataEngine]

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

    def wait_for_volume_deleted(self, volume_name):
        for i in range(self.retry_count):
            logging(f"Waiting for volume {volume_name} deleted ... ({i})")
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

    def wait_for_volume_status(self, volume_name, status, value):
        volume = None
        for i in range(self.retry_count):
            logging(f"Waiting for {volume_name} {status}={value} ({i}) ...")
            try:
                volume = self.get(volume_name)
                if volume["status"][status] == value:
                    break
            except Exception as e:
                logging(f"Getting volume {volume_name} {status} status error: {e}")
            time.sleep(self.retry_interval)
        assert volume["status"][status] == value, \
            f"Expected volume {volume_name} {status}={value},\n" \
            f"but got {volume['status'][status]}\n"

    def wait_for_restore_required_status(self, volume_name, restore_required_state):
        volume = None
        for i in range(self.retry_count):
            logging(f"Waiting for {volume_name} restoreRequired={restore_required_state} ({i}) ...")
            try:
                volume = self.get(volume_name)
                if volume["status"]["restoreRequired"] == restore_required_state:
                    break
            except Exception as e:
                logging(f"Getting volume {volume_name} restoreRequired status error: {e}")
            time.sleep(self.retry_interval)
        assert volume["status"]["restoreRequired"] == restore_required_state, \
            f"Expected volume {volume_name} restoreRequired={restore_required_state},\n" \
            f"but got {volume['status']['restoreRequired']}\n"

    def wait_for_volume_to_be_created(self, volume_name):
        for i in range(self.retry_count):
            logging(f"Waiting for volume {volume_name} to be created ... ({i})")
            try:
                self.get(volume_name)
                return
            except Exception as e:
                logging(f"Failed to wait for volume {volume_name} to be created: {e}")
            time.sleep(self.retry_interval)
        assert False, f"Failed to wait for volume {volume_name} to be created"

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

    def wait_for_volume_attaching(self, volume_name):
        self.wait_for_volume_state(volume_name, "attaching")
        volume = self.get(volume_name)
        assert volume["spec"]["nodeID"] != ""
        assert volume["status"]["currentNodeID"] == ""

    def is_replica_running(self, volume_name, node_name, is_running):
        return Rest().is_replica_running(volume_name, node_name, is_running)

    def get_replica_name_on_node(self, volume_name, node_name):
        return Rest().get_replica_name_on_node(volume_name, node_name)

    def wait_for_replica_count(self, volume_name, node_name, replica_count, running):
        return Rest().wait_for_replica_count(volume_name, node_name, replica_count, running)

    def wait_for_replica_to_be_deleted(self, volume_name, node_name):
        return Rest().wait_for_replica_to_be_deleted(volume_name, node_name)

    def wait_for_volume_keep_in_state(self, volume_name, desired_state):
        self.wait_for_volume_state(volume_name, desired_state)

        keep_state_desire_time = 20
        for i in range(keep_state_desire_time):
            volume = self.get(volume_name)
            logging(f"Checking volume {volume_name} kept in status {desired_state}")
            assert volume["status"]["state"] == desired_state, volume
            time.sleep(self.retry_interval)

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

    def wait_for_volume_migration_to_be_ready(self, volume_name):
        ready = False
        for i in range(self.retry_count):
            logging(f"Waiting for volume {volume_name} migration to be ready ({i}) ...")
            try:
                engines = self.engine.get_engines(volume_name)
                volume = self.get(volume_name)
                ready = len(engines) == 2
                for engine in engines:
                    ready = ready and engine['status']['endpoint']
                ready = volume['spec']['migrationNodeID'] and volume['spec']['migrationNodeID'] == volume['status']['currentMigrationNodeID']
                ready = volume['spec']['nodeID'] and volume['spec']['nodeID'] == volume['status']['currentNodeID']
                if ready:
                    break
            except Exception as e:
                logging(f"Getting volume {volume_name} engines error: {e}")
            time.sleep(self.retry_interval)
        assert ready, f"Waiting for volume {volume_name} migration to be ready failed: engines = {engines}, volume = {volume}"

    def wait_for_volume_migration_complete(self, volume_name, node_name):
        complete = False
        for i in range(self.retry_count):
            logging(f"Waiting for volume {volume_name} migration to node {node_name} complete ({i}) ...")
            try:
                engines = self.engine.get_engines(volume_name)
                volume = self.get(volume_name)
                engine_check = len(engines) == 1 and engines[0]['status']['endpoint'] and engines[0]['status']['ownerID'] == node_name
                migration_node_check = volume['spec']['migrationNodeID'] == "" and volume['status']['currentMigrationNodeID'] == ""
                node_check = volume['spec']['nodeID'] == node_name and volume['spec']['nodeID'] == volume['status']['currentNodeID']
                complete = engine_check and migration_node_check and node_check
                if complete:
                    break
            except Exception as e:
                logging(f"Getting volume {volume_name} engines error: {e}")
            time.sleep(self.retry_interval)
        assert complete, f"Waiting for volume {volume_name} migration complete failed: engines = {engines}, volume = {volume}"

    def wait_for_volume_migration_to_rollback(self, volume_name, node_name):
        rollback = False
        for i in range(self.retry_count):
            logging(f"Waiting for volume {volume_name} migration to rollback to node {node_name} ({i}) ...")
            try:
                engines = self.engine.get_engines(volume_name)
                volume = self.get(volume_name)
                engine_check = len(engines) == 1 and engines[0]['status']['endpoint'] and engines[0]['status']['ownerID'] == node_name
                migration_node_check = volume['spec']['migrationNodeID'] == "" and volume['status']['currentMigrationNodeID'] == ""
                node_check = volume['spec']['nodeID'] == node_name and volume['spec']['nodeID'] == volume['status']['currentNodeID']
                rollback = engine_check and migration_node_check and node_check
                if rollback:
                    break
            except Exception as e:
                logging(f"Getting volume {volume_name} engines error: {e}")
            time.sleep(self.retry_interval)
        assert rollback, f"Waiting for volume {volume_name} migration rollback failed: engines = {engines}, volume = {volume}"

    def wait_for_volume_restoration_to_complete(self, volume_name, backup_name):
        complete = False
        for i in range(self.retry_count):
            logging(f"Waiting for volume {volume_name} restoration from backup {backup_name} to complete ({i}) ...")
            try:
                engines = self.engine.get_engines(volume_name)
                complete = len(engines) == 1 and engines[0]['status']['lastRestoredBackup'] == backup_name
                if complete:
                    break
            except Exception as e:
                logging(f"Getting volume {volume_name} engines error: {e}")
            time.sleep(self.retry_interval)
        assert complete

        volume = self.get(volume_name)
        if not volume['status']['isStandby']:
            self.wait_for_restore_required_status(volume_name, False)

    def wait_for_volume_restoration_start(self, volume_name, backup_name,
                                          progress=0):
        started = False
        for i in range(self.retry_count):
            try:
                engines = self.engine.get_engines(volume_name)
                for engine in engines:
                    for status in engine['status']['restoreStatus'].values():
                        if status['state'] == "in_progress" and status['progress'] > progress:
                            started = True
                            break
                    #  Sometime the restore time is pretty short
                    #  and the test may not be able to catch the intermediate status.
                    if engine['status']['lastRestoredBackup'] == backup_name:
                        started = True
                    if started:
                        break
                if started:
                    break
            except Exception as e:
                logging(f"Getting volume {volume_name} engines error: {e}")
            time.sleep(self.retry_interval)
        assert started

    def wait_for_volume_expand_to_size(self, volume_name, expected_size):
        engine = None
        engine_current_size = 0
        engine_expected_size = int(expected_size)
        engine_operation = Engine()
        for i in range(self.retry_count):
            engine = engine_operation.get_engine(volume_name)
            engine_current_size = int(engine['status']['currentSize'])
            if engine_current_size == engine_expected_size:
                break

            logging(f"Waiting for volume engine expand from {engine_current_size} to {expected_size} ({i}) ...")

            time.sleep(self.retry_interval)

        assert engine is not None
        assert engine_current_size == engine_expected_size

    def get_endpoint(self, volume_name):
        return Rest().get_endpoint(volume_name)

    def write_random_data(self, volume_name, size, data_id):

        self.wait_for_volume_state(volume_name, "attached")

        for i in range(self.retry_count):
            node_name = self.get(volume_name)["spec"]["nodeID"]
            if node_name:
                break
            time.sleep(self.retry_interval)

        endpoint = self.get_endpoint(volume_name)

        cmd = [
            "sh", "-c",
            f"dd if=/dev/urandom of={endpoint} bs=1M count={size} status=none; "
            "sync; "
            f"md5sum {endpoint} | awk '{{print $1}}' | tr -d ' \n'"
        ]
        checksum = NodeExec(node_name).issue_cmd(cmd)

        if data_id:
            logging(f"Storing volume {volume_name} data {data_id} checksum = {checksum}")
            self.set_data_checksum(volume_name, data_id, checksum)
        logging(f"Storing volume {volume_name} data last recorded checksum = {checksum}")
        self.set_last_data_checksum(volume_name, checksum)
        return checksum

    def keep_writing_data(self, volume_name, size):

        self.wait_for_volume_state(volume_name, "attached")

        for i in range(self.retry_count):
            node_name = self.get(volume_name)["spec"]["nodeID"]
            if node_name:
                break
            time.sleep(self.retry_interval)

        endpoint = self.get_endpoint(volume_name)
        logging(f"Keeping writing data to volume {volume_name}")
        res = NodeExec(node_name).issue_cmd(
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

    def delete_replica_by_name(self, volume_name, replica_name):
        replica = self.obj_api.get_namespaced_custom_object(
            group="longhorn.io",
            version="v1beta2",
            namespace="longhorn-system",
            plural="replicas",
            name=replica_name
        )
        logging(f"Deleting replica {replica['metadata']['name']}")
        self.obj_api.delete_namespaced_custom_object(
            group="longhorn.io",
            version="v1beta2",
            namespace="longhorn-system",
            plural="replicas",
            name=replica['metadata']['name']
        )

    def wait_for_replica_rebuilding_start(self, volume_name, node_name):
        return Rest().wait_for_replica_rebuilding_start(volume_name, node_name)

    def is_replica_rebuilding_in_progress(self, volume_name, node_name):
        return Rest().is_replica_rebuilding_in_progress(volume_name, node_name)

    def crash_replica_processes(self, volume_name):
        return Rest().crash_replica_processes(volume_name)

    def crash_node_replica_process(self, volume_name, node_name):
        return Rest().crash_node_replica_process(volume_name, node_name)

    def wait_for_replica_rebuilding_complete(self, volume_name, node_name=None):
        return Rest().wait_for_replica_rebuilding_complete(volume_name, node_name)

    def check_data_checksum(self, volume_name, data_id):
        expected_checksum = self.get_data_checksum(volume_name, data_id)
        actual_checksum = self.get_checksum(volume_name)
        logging(f"Checked volume {volume_name} data {data_id}. Expected checksum = {expected_checksum}. Actual checksum = {actual_checksum}")
        if actual_checksum != expected_checksum:
            message = f"Checked volume {volume_name} data {data_id} failed. Expected checksum = {expected_checksum}. Actual checksum = {actual_checksum}"
            logging(message)
            time.sleep(self.retry_count)
            assert False, message

    def get_checksum(self, volume_name):
        node_name = self.get(volume_name)["spec"]["nodeID"]
        endpoint = self.get_endpoint(volume_name)
        checksum = NodeExec(node_name).issue_cmd(
            ["sh", "-c", f"md5sum {endpoint} | awk '{{print $1}}' | tr -d ' \n'"])
        logging(f"Calculated volume {volume_name} checksum {checksum}")
        return checksum

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

    def update_volume_spec(self, volume_name, key, value):
        # retry conflict error
        for i in range(self.retry_count):
            try:
                volume = self.get(volume_name)
                spec = volume['spec']
                if key == "numberOfReplicas":
                    spec[key] = int(value)
                else:
                    spec[key] = value
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

    def activate(self, volume_name):
        return Rest().activate(volume_name)

    def create_persistentvolume(self, volume_name, retry):
        return Rest().create_persistentvolume(volume_name, retry)

    def create_persistentvolumeclaim(self, volume_name, retry):
        return Rest().create_persistentvolumeclaim(volume_name, retry)

    def upgrade_engine_image(self, volume_name, engine_image_name):
        return Rest().upgrade_engine_image(volume_name, engine_image_name)

    def wait_for_engine_image_upgrade_completed(self, volume_name, engine_image_name):
        return Rest().wait_for_engine_image_upgrade_completed(volume_name, engine_image_name)

    def validate_volume_setting(self, volume_name, setting_name, value):
        volume = self.get(volume_name)
        assert str(volume["spec"][setting_name]) == value, \
            f"Expected volume {volume_name} setting {setting_name} is {value}, but it's {str(volume['spec'][setting_name])}"

    def trim_filesystem(self, volume_name, is_expect_fail=False):
        return Rest(self).trim_filesystem(volume_name, is_expect_fail=is_expect_fail)

    def update_offline_replica_rebuild(self, volume_name, rebuild_type):
        return Rest().update_offline_replica_rebuild(volume_name, rebuild_type)
