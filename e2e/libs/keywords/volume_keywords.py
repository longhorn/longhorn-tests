import asyncio
import time

from node import Node
from node.utility import check_replica_locality

from replica import Replica

from utility.constant import ANNOT_REPLICA_NAMES
from utility.constant import LABEL_TEST
from utility.constant import LABEL_TEST_VALUE
import utility.constant as constant
from utility.utility import logging
from utility.utility import get_retry_count_and_interval

from volume import Volume
from volume.rest import Rest as VolumeRest


class volume_keywords:

    def __init__(self):
        self.node = Node()
        self.volume = Volume()
        self.replica = Replica()

    def cleanup_volumes(self):
        volumes = self.volume.list(label_selector=f"{LABEL_TEST}={LABEL_TEST_VALUE}")

        logging(f'Cleaning up {len(volumes)} volumes')
        for volume in volumes:
            self.delete_volume(volume['metadata']['name'])

    def create_volume(self, volume_name, size="2Gi", numberOfReplicas=3, frontend="blockdev", migratable=False, dataLocality="disabled", accessMode="RWO", dataEngine="v1", backingImage="", Standby=False, fromBackup="", encrypted=False, nodeSelector=[], diskSelector=[], backupBlockSize="2Mi"):
        logging(f'Creating volume {volume_name}')
        self.volume.create(volume_name, size, numberOfReplicas, frontend, migratable, dataLocality, accessMode, dataEngine, backingImage, Standby, fromBackup, encrypted, nodeSelector, diskSelector, backupBlockSize)

    def delete_volume(self, volume_name, wait=True):
        logging(f'Deleting volume {volume_name}')
        self.volume.delete(volume_name, wait)

    def attach_volume(self, volume_name, node_name=None, wait=True, retry=True):
        if not node_name:
            node_name = self.node.get_node_by_index(0)
        logging(f'Attaching volume {volume_name} to node {node_name}')
        self.volume.attach(volume_name, node_name, disable_frontend=False, wait=wait, retry=retry)

    def is_attached_to(self, volume_name, node_name):
        return self.volume.is_attached_to(volume_name, node_name)

    def attach_volume_in_maintenance_mode(self, volume_name, node_name=None, wait=True, retry=True):
        if not node_name:
            node_name = self.node.get_node_by_index(0)
        logging(f'Attaching volume {volume_name} to node {node_name} in maintenance mode')
        self.volume.attach(volume_name, node_name, disable_frontend=True, wait=wait, retry=retry)

    def detach_volume(self, volume_name, node_name=None):
        if not node_name:
            node_name = self.node.get_node_by_index(0)
        logging(f'Detaching volume {volume_name} from node {node_name}')
        self.volume.detach(volume_name, node_name)

    def list_volumes(self, dataEngine=None):
        logging(f'Listing volumes')
        return self.volume.list_names(dataEngine=dataEngine)

    def wait_for_volume_expand_to_size(self, volume_name, size):
        logging(f'Waiting for volume {volume_name} expand to {size}')
        return self.volume.wait_for_volume_expand_to_size(volume_name, size)

    def get_replica_node(self, volume_name):
        return self.get_node_id_by_replica_locality(volume_name, "replica node")

    def get_volume_node(self, volume_name):
        return self.get_node_id_by_replica_locality(volume_name, "volume node")

    def get_volume_instance_manager(self, volume_name):
        volume = VolumeRest().get(volume_name)
        assert len(volume['controllers']) == 1, f"Expect only one controller for volume {volume_name}; Got controllers: {volume['controllers']}"
        return volume['controllers'][0]['instanceManagerName']

    def get_node_id_by_replica_locality(self, volume_name, replica_locality):
        return self.get_node_ids_by_replica_locality(volume_name, replica_locality)[0]

    def get_node_ids_by_replica_locality(self, volume_name, replica_locality):
        check_replica_locality(replica_locality)

        if replica_locality == "volume node":
            volume = self.volume.get(volume_name)
            return [volume['spec']['nodeID']]

        worker_nodes = self.node.list_node_names_by_role("worker")
        volume_node = self.get_node_id_by_replica_locality(volume_name, "volume node")
        replica_nodes = [node for node in worker_nodes if node != volume_node]

        if replica_locality == "replica node":
            return replica_nodes

        else:
            raise ValueError(f"Unknown replica locality {replica_locality}")

        raise Exception(f"Failed to get node ID of the replica on {replica_locality}")

    def write_volume_random_data(self, volume_name, size_in_mb, data_id=None):
        logging(f'Writing {size_in_mb} MB random data to volume {volume_name}')
        return self.volume.write_random_data(volume_name, size_in_mb, data_id)

    def keep_writing_data(self, volume_name):
        logging(f'Keep writing data to volume {volume_name}')
        self.volume.keep_writing_data(volume_name)

    def check_data_checksum(self, volume_name, data_id=0):
        logging(f"Checking volume {volume_name} data {data_id} checksum")
        return self.volume.check_data_checksum(volume_name, data_id)

    def delete_replica_on_node(self, volume_name, replica_locality):
        node_name = None
        if index := self.node.is_accessing_node_by_index(replica_locality):
            node_name = self.node.get_node_by_index(index)
        else:
            node_name = self.get_node_id_by_replica_locality(volume_name, replica_locality)

        logging(f"Deleting volume {volume_name}'s replica on node {node_name}")
        retry_count, retry_interval = get_retry_count_and_interval()
        for _ in range(retry_count):
            try:
                self.volume.delete_replica(volume_name, node_name)
                return
            except Exception as e:
                logging(f"Deleting volume {volume_name}'s replica on node {node_name} failed with error: {e} ... ({_})")
                time.sleep(retry_interval)

    def delete_replica_on_nodes(self, volume_name, replica_locality):
        check_replica_locality(replica_locality)

        node_ids = self.get_node_ids_by_replica_locality(volume_name, replica_locality)
        for node_id in node_ids:
            logging(f"Deleting volume {volume_name}'s replica on node {node_id}")
            self.volume.delete_replica(volume_name, node_id)

    def delete_replicas(self, volume_name, count):
        replica_list = self.replica.get(volume_name, node_name="")
        replica_names = [replica['metadata']['name'] for replica in replica_list]
        for i in range(int(count)):
            logging(f"Deleting volume {volume_name} replica volume {replica_names[i]}")
            self.volume.delete_replica_by_name(volume_name, replica_names[i])

    def set_annotation(self, volume_name, annotation_key, annotation_value):
        self.volume.set_annotation(volume_name, annotation_key, annotation_value)

    async def wait_for_replica_rebuilding_to_start_on_node(self, volume_name, replica_locality):
        node_name = None
        if index := self.node.is_accessing_node_by_index(replica_locality):
            node_name = self.node.get_node_by_index(index)
        else:
            node_name = self.get_node_id_by_replica_locality(volume_name, replica_locality)

        logging(f"Waiting for volume {volume_name}'s replica on node {node_name} rebuilding started")
        await self.volume.wait_for_replica_rebuilding_start(volume_name, node_name)

    def wait_for_replica_rebuilding_to_complete_on_node(self, volume_name, replica_locality):
        node_name = None
        if index := self.node.is_accessing_node_by_index(replica_locality):
            node_name = self.node.get_node_by_index(index)
        else:
            node_name = self.get_node_id_by_replica_locality(volume_name, replica_locality)

        logging(f"Waiting for volume {volume_name}'s replica on node {node_name} rebuilding completed")
        start_time = time.time()
        self.volume.wait_for_replica_rebuilding_complete(volume_name, node_name)
        rebuilding_time = int(time.time() - start_time)
        logging(f"Replica rebuilding for volume {volume_name} on node {node_name} completed in {rebuilding_time} seconds")
        return rebuilding_time

    def wait_for_replica_rebuilding_to_complete(self, volume_name):
        self.volume.wait_for_replica_rebuilding_complete(volume_name)

    async def only_one_replica_rebuilding_will_start_at_a_time_on_node(self, volume_name_0, volume_name_1, replica_locality):

        node_id = self.get_node_id_by_replica_locality(volume_name_0, replica_locality)

        first_replica_rebuilding = None
        not_start_replica_rebuilding = None

        async def find_first_replica_rebuilding():
            tasks = [
                asyncio.create_task(self.volume.wait_for_replica_rebuilding_start(volume_name_0, node_id), name=volume_name_0),
                asyncio.create_task(self.volume.wait_for_replica_rebuilding_start(volume_name_1, node_id), name=volume_name_1)
            ]

            done, pending = await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)
            for pending_task in pending:
                pending_task.cancel()
            return done.pop().get_name(), pending.pop().get_name()

        first_replica_rebuilding, not_start_replica_rebuilding = await find_first_replica_rebuilding()
        logging(f"Observed {first_replica_rebuilding} started replica rebuilding first")

        while self.volume.is_replica_rebuilding_in_progress(first_replica_rebuilding, node_id):
            logging(f"Checking volume {not_start_replica_rebuilding} replica rebuilding won't start \
                if volume {first_replica_rebuilding} replica rebuilding is still in progress")
            assert not self.volume.is_replica_rebuilding_in_progress(not_start_replica_rebuilding, node_id)
            time.sleep(1)

    async def both_replica_rebuildings_will_start_at_the_same_time_on_node(self, volume_name_0, volume_name_1, replica_locality):

        node_id = self.get_node_id_by_replica_locality(volume_name_0, replica_locality)

        async def wait_for_both_replica_rebuildings():
            tasks = [
                asyncio.create_task(self.volume.wait_for_replica_rebuilding_start(volume_name_0, node_id), name=volume_name_0),
                asyncio.create_task(self.volume.wait_for_replica_rebuilding_start(volume_name_1, node_id), name=volume_name_1)
            ]

            done, pending = await asyncio.wait(tasks, return_when=asyncio.ALL_COMPLETED)
            for task in done:
                if task.exception():
                    assert False, task.exception()
            logging(f"Observed {done.pop().get_name()} and {done.pop().get_name()} started replica rebuilding first")

        await wait_for_both_replica_rebuildings()

        assert self.volume.is_replica_rebuilding_in_progress(volume_name_0, node_id) and self.volume.is_replica_rebuilding_in_progress(volume_name_1, node_id), \
            f"Expect {volume_name_0} and {volume_name_1} replica rebuilding at the same time"

    async def only_one_replica_rebuilding_will_start_at_a_time(self, volume_name):

        async def wait_for_replica_rebuilding():
            tasks = [
                asyncio.create_task(self.volume.wait_for_replica_rebuilding_start(volume_name), name=volume_name),
            ]

            done, pending = await asyncio.wait(tasks, return_when=asyncio.ALL_COMPLETED)
            for task in done:
                if task.exception():
                    assert False, task.exception()
            logging(f"Observed {done.pop().get_name()} started replica rebuilding")

        await wait_for_replica_rebuilding()

        assert self.volume.is_replica_rebuilding_in_progress(volume_name), \
            f"Expect {volume_name} replica rebuilding in progress"

    def crash_replica_processes(self, volume_name):
        self.volume.crash_replica_processes(volume_name)

    def crash_node_replica_process(self, volume_name, node_name):
        return self.volume.crash_node_replica_process(volume_name, node_name)

    def wait_for_replica_stopped(self, volume_name, node_name):
        self.volume.wait_for_replica_stopped(volume_name, node_name)

    def wait_for_replica_to_be_deleted(self, volume_name, node_name):
        self.volume.wait_for_replica_to_be_deleted(volume_name, node_name)

    def wait_for_replica_running(self, volume_name, node_name):
        self.volume.wait_for_replica_running(volume_name, node_name)

    def get_replica_name_on_node(self, volume_name, node_name):
        return self.volume.get_replica_name_on_node(volume_name, node_name)

    def wait_for_replica_count(self, volume_name, node_name=None, replica_count=None, running=True):
        return self.volume.wait_for_replica_count(volume_name, node_name, replica_count, running)

    def wait_for_replica_rebuilding_to_stop_on_node(self, volume_name, replica_locality):
        node_id = self.get_node_id_by_replica_locality(volume_name, replica_locality)
        retry_count, retry_interval = get_retry_count_and_interval()
        for i in range(retry_count):
            if not self.volume.is_replica_rebuilding_in_progress(volume_name, node_id):
                break
            time.sleep(retry_interval)

    def wait_for_volume_to_be_created(self, volume_name):
        logging(f'Waiting for volume {volume_name} to be created')
        self.volume.wait_for_volume_to_be_created(volume_name)

    def wait_for_volume_attached(self, volume_name):
        logging(f'Waiting for volume {volume_name} to be attached')
        self.volume.wait_for_volume_attached(volume_name)

    def wait_for_volume_detached(self, volume_name):
        logging(f'Waiting for volume {volume_name} to be detached')
        self.volume.wait_for_volume_detached(volume_name)

    def wait_for_volume_healthy(self, volume_name):
        logging(f'Waiting for volume {volume_name} to be healthy')
        self.volume.wait_for_volume_healthy(volume_name)

    def wait_for_volume_attaching(self, volume_name):
        logging(f'Waiting for volume {volume_name} to be in attaching')
        self.volume.wait_for_volume_attaching(volume_name)

    def wait_for_volume_stuck_attaching(self, volume_name):
        logging(f'Waiting for volume {volume_name} to be stuck at attaching')
        self.volume.wait_for_volume_stuck_attaching(volume_name)

    def wait_for_volume_faulted(self, volume_name):
        logging(f'Waiting for volume {volume_name} to be in faulted')
        self.volume.wait_for_volume_faulted(volume_name)

    def wait_for_volume_condition(self, volume_name, condition_name, condition_status, reason=""):
        self.volume.wait_for_volume_condition(volume_name, condition_name, condition_status, reason)

    def wait_for_volume_clone_status_completed(self, volume_name):
        logging(f'Waiting for volume {volume_name} clone status to be completed')
        self.volume.wait_for_volume_clone_status(volume_name, "completed")

    def wait_for_volume_migration_to_be_ready(self, volume_name):
        logging(f'Waiting for volume {volume_name} migration to be ready')
        self.volume.wait_for_volume_migration_to_be_ready(volume_name)

    def wait_for_volume_migration_complete(self, volume_name, node_name):
        logging(f'Waiting for volume {volume_name} migration to node {node_name} complete')
        self.volume.wait_for_volume_migration_complete(volume_name, node_name)

    def wait_for_volume_migration_to_rollback(self, volume_name, node_name):
        logging(f'Waiting for volume {volume_name} migration to rollback to node {node_name}')
        self.volume.wait_for_volume_migration_to_rollback(volume_name, node_name)

    def wait_for_volume_restoration_to_complete(self, volume_name, backup_name=None):
        logging(f'Waiting for volume {volume_name} restoration to complete')
        self.volume.wait_for_volume_restoration_to_complete(volume_name, backup_name)

    def wait_for_volume_restoration_start(self, volume_name, backup_name):
        logging(f'Waiting for volume {volume_name} restoration from {backup_name} start')
        self.volume.wait_for_volume_restoration_start(volume_name, backup_name)

    def validate_volume_replicas_anti_affinity(self, volume_name):
        self.volume.validate_volume_replicas_anti_affinity(volume_name)

    def wait_for_volume_degraded(self, volume_name):
        self.volume.wait_for_volume_degraded(volume_name)

    def wait_for_volume_unknown(self, volume_name):
        self.volume.wait_for_volume_unknown(volume_name)

    def wait_for_volume_deleted(self, volume_name):
        self.volume.wait_for_volume_deleted(volume_name)

    def update_volume_spec(self, volume_name, key, value):
        self.volume.update_volume_spec(volume_name, key, value)

    def activate_dr_volume(self, volume_name):
        self.volume.activate(volume_name)

    def create_persistentvolume_for_volume(self, volume_name, retry=True):
        self.volume.create_persistentvolume(volume_name, retry)

    def create_persistentvolumeclaim_for_volume(self, volume_name, retry=True):
        self.volume.create_persistentvolumeclaim(volume_name, retry)

    def record_volume_replica_names(self, volume_name):
        replica_list = self.replica.get(volume_name, node_name="")
        replica_names = [replica['metadata']['name'] for replica in replica_list]
        logging(f"Found volume {volume_name} replicas: {replica_names}")

        replica_names_str = ",".join(replica_names)
        self.volume.set_annotation(volume_name, ANNOT_REPLICA_NAMES, replica_names_str)

    def check_volume_replica_names_recorded(self, volume_name):
        replica_names_str = self.volume.get_annotation_value(volume_name, ANNOT_REPLICA_NAMES)
        expected_replica_names = sorted(replica_names_str.split(","))

        replica_list = self.replica.get(volume_name, node_name="")
        actual_replica_names = [replica['metadata']['name'] for replica in replica_list]
        actual_replica_names = sorted(actual_replica_names)

        assert actual_replica_names == expected_replica_names, \
            f"The volume should reuse the failed replica to rebuild instead of creating a new one.\n" \
            f"Volume {volume_name} replica names mismatched:\n" \
            f"Want: {expected_replica_names}\n" \
            f"Got: {actual_replica_names}"

    def upgrade_engine_image(self, volume_name, engine_image_name):
        self.volume.upgrade_engine_image(volume_name, engine_image_name)

    def wait_for_engine_image_upgrade_completed(self, volume_name, engine_image_name):
        self.volume.wait_for_engine_image_upgrade_completed(volume_name, engine_image_name)

    def get_volume_checksum(self, volume_name):
        return self.volume.get_checksum(volume_name)

    def validate_volume_setting(self, volume_name, setting_name, value):
        return self.volume.validate_volume_setting(volume_name, setting_name, value)

    def get_volume_size(self, volume_name):
        volume = self.volume.get(volume_name)
        return volume['spec']['size']

    def get_volume_node_disk_storage_maximum(self, volume_name, node_name):
        replica_list = self.replica.get(volume_name, node_name)
        replica = replica_list[0]
        replica_name = replica['metadata']['name']
        node = self.node.get_node_by_name(node_name, namespace=constant.LONGHORN_NAMESPACE)
        for diskName in node.disks:
            disk = node.disks[diskName]

            for scheduledReplica in disk['scheduledReplica']:
                if scheduledReplica == replica_name:
                    logging(f"Found replica {scheduledReplica} on node {node_name} scheduled to disk {diskName}")
                    return disk['storageMaximum']

        raise Exception(f"Failed to find storageMaximum for volume {volume_name} replica {replica_name} on node {node_name}")

    def update_offline_replica_rebuild(self, volume_name, rebuild_type="ignore"):
        logging(f'Volume {volume_name} offline replica rebuilding is updating to {rebuild_type}')
        self.volume.update_offline_replica_rebuild(volume_name, rebuild_type)

    def update_data_locality(self, volume_name, data_locality):
        logging(f'Updating volume {volume_name} data locality {data_locality}')
        self.volume.update_data_locality(volume_name, data_locality)

    def check_volume_has_recurringjob(self, volume_name, job_name):
        self.volume.check_volume_has_recurringjob(volume_name, job_name)

    def check_volume_has_recurringjob_group(self, volume_name, job_group_name):
        self.volume.check_volume_has_recurringjob_group(volume_name, job_group_name)
