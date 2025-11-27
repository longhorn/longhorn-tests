import os
import time
import asyncio

from node_exec import NodeExec

from persistentvolumeclaim.persistentvolumeclaim import PersistentVolumeClaim
from persistentvolume.persistentvolume import PersistentVolume

from volume.base import Base
from volume.constant import DEV_PATH
from volume.constant import VOLUME_FRONTEND_BLOCKDEV
from volume.constant import VOLUME_FRONTEND_ISCSI

import utility.constant as constant
from utility.utility import get_retry_count_and_interval
from utility.utility import get_longhorn_client
from utility.utility import logging
from utility.utility import pod_exec


class Rest(Base):

    def __init__(self):
        self.retry_count, self.retry_interval = get_retry_count_and_interval()
        self.pv = PersistentVolume()
        self.pvc = PersistentVolumeClaim()

    def get(self, volume_name):
        for i in range(self.retry_count):
            try:
                return get_longhorn_client().by_id_volume(volume_name)
            except Exception as e:
                logging(f"Failed to get volume {volume_name} with error: {e}")
            time.sleep(self.retry_interval)

    def list(self):
        vol_list = []
        for i in range(self.retry_count):
            logging(f"Try to list volumes ... ({i})")
            try:
                volumes = get_longhorn_client().list_volume()
                for volume in volumes:
                    vol_list.append(volume.name)
                break
            except Exception as e:
                logging(f"Failed to list volumes with error: {e}")
            time.sleep(self.retry_interval)
        return vol_list

    def create(self, volume_name, size, numberOfReplicas, frontend, migratable, dataLocality, accessMode, dataEngine, backingImage, Standby, fromBackup, encrypted, backupBlockSize):
        return NotImplemented

    def attach(self, volume_name, node_name, disable_frontend, wait, retry):
        return NotImplemented

    def is_attached_to(self, volume_name, node_name):
        logging(f"Checking volume {volume_name} is attached to node {node_name}")
        v = self.get(volume_name)
        for attachment in v.volumeAttachment.attachments.values():
            if attachment.nodeID == node_name:
                return True
        return False

    def detach(self, volume_name, node_name):
        return NotImplemented

    def delete(self, volume_name):
        return NotImplemented

    def wait_for_volume_to_be_created(self, volume_name):
        return NotImplemented

    def wait_for_volume_state(self, volume_name, desired_state):
        for i in range(self.retry_count):
            volume = self.get(volume_name)
            if volume['state'] == desired_state:
                break
            time.sleep(self.retry_interval)
        assert volume['state'] == desired_state

    def wait_for_volume_clone_status(self, volume_name, desired_state):
        for i in range(self.retry_count):
            try:
                volume = self.get(volume_name)
                logging(f"Waiting for volume {volume_name} cloneStatus to be {desired_state} ... ({i})")
                if volume['cloneStatus']['status'] == desired_state:
                    return
            except Exception as e:
                logging(f"Waiting for volume {volume_name} cloneStatus to be {desired_state} error: {e}")
            time.sleep(self.retry_interval)
        assert False, f"Failed to wait for volume {volume_name} cloneStatus to be {desired_state}: {volume}"

    def wait_for_restore_required_status(self, volume_name, restore_required_state):
        return NotImplemented

    def wait_for_volume_migration_to_be_ready(self, volume_name):
        return NotImplemented

    def wait_for_volume_migration_complete(self, volume_name, node_name):
        return NotImplemented

    def wait_for_volume_migration_to_rollback(self, volume_name, node_name):
        return NotImplemented

    def wait_for_volume_restoration_to_complete(self, volume_name, backup_name):
        return NotImplemented

    def wait_for_volume_restoration_start(self, volume_name):
        return NotImplemented

    def get_endpoint(self, volume_name):
        endpoint = ""
        v = self.get(volume_name)
        if v.disableFrontend:
            assert endpoint == ""
            return endpoint
        else:
            assert v.frontend == VOLUME_FRONTEND_BLOCKDEV or\
                   v.frontend == VOLUME_FRONTEND_ISCSI
            for i in range(self.retry_count):
                try:
                    v = get_longhorn_client().by_id_volume(volume_name)
                    engines = v.controllers
                    assert len(engines) != 0
                    endpoint = engines[0].endpoint
                    if endpoint != "":
                        break
                except Exception as e:
                    logging(f"Failed to get volume {volume_name} with error: {e}")
                time.sleep(self.retry_interval)

        logging(f"Got volume {volume_name} endpoint = {endpoint}")

        if v.frontend == VOLUME_FRONTEND_BLOCKDEV:
            assert endpoint == os.path.join(DEV_PATH, v.name)
        elif v.frontend == VOLUME_FRONTEND_ISCSI:
            assert endpoint.startswith("iscsi://")
        return endpoint

    def write_random_data(self, volume_name, size, data_id):
        return NotImplemented

    def keep_writing_data(self, volume_name, size):
        return NotImplemented

    def delete_replica(self, volume_name, node_name):
        return NotImplemented

    async def wait_for_replica_rebuilding_start(self, volume_name, node_name=None):
        rebuilding_replica_name = None
        for i in range(self.retry_count):
            try:
                v = get_longhorn_client().by_id_volume(volume_name)
                logging(f"Trying to get volume {volume_name} rebuilding replicas ... ({i})")
                for replica in v.replicas:
                    if node_name and replica.hostId == node_name and replica.mode == "WO":
                        rebuilding_replica_name = replica.name
                        break
                    elif replica.mode == "WO":
                        rebuilding_replica_name = replica.name
                        node_name = replica.hostId
                        break
                if rebuilding_replica_name:
                    break
            except Exception as e:
                logging(f"Failed to get volume {volume_name} with error: {e}")
            await asyncio.sleep(self.retry_interval)
        assert rebuilding_replica_name != None, f"Waiting for replica rebuilding start for volume {volume_name} on node {node_name} failed: replicas = {v.replicas}"
        logging(f"Got volume {volume_name} rebuilding replica = {rebuilding_replica_name} on node {node_name}")

        started = False
        for i in range(self.retry_count):
            try:
                v = get_longhorn_client().by_id_volume(volume_name)
                logging(f"Got volume {volume_name} rebuild status = {v.rebuildStatus}")

                # During monitoring replica rebuilding
                # at the same time monitoring if there are unexpected concurrent replica rebuilding
                rebuilding_count = 0
                for replica in v.replicas:
                    if replica.mode == "WO":
                        rebuilding_count +=1
                assert rebuilding_count <= 1, f"Unexpected concurrent replica rebuilding = {rebuilding_count}, replicas = {v.replicas}"

                for status in v.rebuildStatus:
                    for replica in v.replicas:
                        if status.replica == replica.name and \
                           replica.hostId == node_name and \
                           status.state == "in_progress":
                            logging(f"Volume {volume_name} started replica rebuilding {replica.name} on {node_name}")
                            started = True
                            break
                if started:
                    break
            except Exception as e:
                logging(f"Failed to get volume {volume_name} with error: {e}")
            await asyncio.sleep(self.retry_interval)
        assert started, f"wait for replica on node {node_name} rebuilding timeout: {v}"

    def is_replica_rebuilding_in_progress(self, volume_name, node_name=None):
        in_progress = False
        for i in range(self.retry_count):
            try:
                v = get_longhorn_client().by_id_volume(volume_name)
                logging(f"Got volume {volume_name} rebuild status = {v.rebuildStatus}")
                for status in v.rebuildStatus:
                    for replica in v.replicas:
                        if status.replica == replica.name and \
                           (node_name is None or replica.hostId == node_name) and \
                           status.state == "in_progress":
                            node_name = replica.hostId if not node_name else node_name
                            logging(f"Volume {volume_name} replica rebuilding {replica.name} in progress on {node_name}")
                            in_progress = True
                break
            except Exception as e:
                logging(f"Failed to get volume {volume_name} with error: {e}")
            time.sleep(self.retry_interval)
        return in_progress

    def crash_replica_processes(self, volume_name):
        logging(f"Crashing volume {volume_name} replica processes")
        replica_map = {}
        volume = get_longhorn_client().by_id_volume(volume_name)
        for r in volume.replicas:
            replica_map[r.instanceManagerName] = r.name

        for rm_name, r_name in replica_map.items():
            delete_command = 'longhorn-instance-manager process delete ' + \
                         '--name ' + r_name
            pod_exec(rm_name, constant.LONGHORN_NAMESPACE, delete_command)

    def crash_node_replica_process(self, volume_name, node_name):
        logging(f"Crashing volume {volume_name} replica process on node {node_name}")
        volume = get_longhorn_client().by_id_volume(volume_name)
        r_name = None
        for r in volume.replicas:
            if r.hostId == node_name:
                rm_name = r.instanceManagerName
                r_name = r.name
                delete_command = 'longhorn-instance-manager process delete ' + \
                             '--name ' + r_name
                pod_exec(rm_name, constant.LONGHORN_NAMESPACE, delete_command)

        return r_name

    def is_replica_running(self, volume_name, node_name, is_running):
        for i in range(self.retry_count):
            volume = get_longhorn_client().by_id_volume(volume_name)
            for r in volume.replicas:
                if r.hostId == node_name and r.running == is_running:
                    return

        assert False, f"Volume {volume_name} replica on node {node_name} running state is not {is_running}"

    def get_replica_name_on_node(self, volume_name, node_name):
        for i in range(self.retry_count):
            volume = get_longhorn_client().by_id_volume(volume_name)
            for r in volume.replicas:
                if r.hostId == node_name:
                    return r.name

    def wait_for_replica_count(self, volume_name, node_name, replica_count, running):
        condition_met = False
        mode = "RW" if running else ""
        for i in range(self.retry_count):
            running_replica_count = 0
            volume = get_longhorn_client().by_id_volume(volume_name)
            for r in volume.replicas:
                if node_name and r.hostId == node_name:
                    # if running == True, it collects running replicas
                    # if running == False, it collects stopped replicas
                    # if running == None, it collects all replicas
                    if running is not None and r.running == running and r.mode == mode:
                        running_replica_count += 1
                    elif running is None:
                        running_replica_count += 1
                elif not node_name:
                    if running is not None and r.running == running and r.mode == mode:
                        running_replica_count += 1
                    elif running is None:
                        running_replica_count += 1
            logging(f"Waiting for {replica_count if replica_count else ''} replicas for volume {volume_name} running={running} on {node_name if node_name else 'nodes'}, currently it's {running_replica_count} ... ({i})")
            if replica_count and running_replica_count == int(replica_count):
                condition_met = True
                break
            elif not replica_count and running_replica_count:
                condition_met = True
                break
            time.sleep(self.retry_interval)
        assert condition_met, f"Waiting for {replica_count if replica_count else ''} replicas for volume {volume_name} running={running} on {node_name if node_name else 'nodes'} failed. There are only {running_replica_count} replicas"
        return running_replica_count

    def wait_for_replica_to_be_deleted(self, volume_name, node_name):
        for i in range(self.retry_count):
            deleted = True
            logging(f"Waiting for volume {volume_name} replica on {node_name} to be deleted ... ({i})")
            volume = get_longhorn_client().by_id_volume(volume_name)
            for r in volume.replicas:
                if node_name == r.hostId:
                    deleted = False
                    break
            if deleted:
                return
            time.sleep(self.retry_interval)
        assert False, f"Failed to wait for volume {volume_name} replica on {node_name} to be deleted: {volume.replicas}"

    def wait_for_replica_rebuilding_complete(self, volume_name, node_name=None):
        completed = False
        for i in range(self.retry_count):
            logging(f"wait for {volume_name} replica rebuilding completed on {'all nodes' if not node_name else node_name} ... ({i})")
            try:
                v = get_longhorn_client().by_id_volume(volume_name)

                # During monitoring replica rebuilding
                # at the same time monitoring if there are unexpected concurrent replica rebuilding
                rebuilding_count = 0
                for replica in v.replicas:
                    if replica.mode == "WO":
                        rebuilding_count +=1
                assert rebuilding_count <= 1, f"Unexpected concurrent replica rebuilding = {rebuilding_count}, replicas = {v.replicas}"

                if node_name:
                    for replica in v.replicas:
                        # use replica.mode is RW or RO to check if this replica
                        # has been rebuilt or not
                        # because rebuildStatus is not reliable
                        # when the rebuild progress reaches 100%
                        # it will be removed from rebuildStatus immediately
                        # and you will just get an empty rebuildStatus []
                        # so it's no way to distinguish "rebuilding not started yet"
                        # or "rebuilding already completed" using rebuildStatus
                        if replica.hostId == node_name and replica.mode == "RW":
                            completed = True
                            break
                else:
                    rw_replica_count = 0
                    for replica in v.replicas:
                        if replica.mode == "RW":
                            rw_replica_count += 1
                    if rw_replica_count == v.numberOfReplicas:
                        completed = True
                if completed:
                    break
            except Exception as e:
                logging(f"Failed to get volume {volume_name} with error: {e}")
            time.sleep(self.retry_interval)
        logging(f"Completed volume {volume_name} replica rebuilding on {'all nodes' if not node_name else node_name}")
        assert completed, f"Expect volume {volume_name} replica rebuilding completed on {'all nodes' if not node_name else node_name}"

    def check_data_checksum(self, volume_name, data_id):
        return NotImplemented

    def get_checksum(self, volume_name):
        node_name = self.get(volume_name).controllers[0].hostId
        endpoint = self.get_endpoint(volume_name)
        checksum = NodeExec(node_name).issue_cmd(
            ["sh", "-c", f"md5sum {endpoint} | awk '{{print $1}}' | tr -d ' \n'"])
        logging(f"Calculated volume {volume_name} checksum {checksum}")
        return checksum

    def cleanup(self, volume_names):
        return NotImplemented

    def update_volume_spec(self, volume_name, key, value):
        return NotImplemented

    def activate(self, volume_name):
        for i in range(self.retry_count):
            logging(f"Activating volume {volume_name} ... ({i})")
            volume = self.get(volume_name)
            engines = volume.controllers
            if len(engines) != 1 or \
                (volume.lastBackup != "" and
                 engines[0].lastRestoredBackup != volume.lastBackup):
                time.sleep(self.retry_interval)
                continue
            activated = False
            try:
                volume.activate(frontend=VOLUME_FRONTEND_BLOCKDEV)
                activated = True
                break
            except Exception as e:
                logging(f"Activating volume {volume_name} error: {e}")
                assert "hasn't finished incremental restored" in str(e.error.message)
                time.sleep(self.retry_interval)
            if activated:
                break
        volume = self.get(volume_name)
        assert volume.standby is False
        assert volume.frontend == VOLUME_FRONTEND_BLOCKDEV

        self.wait_for_volume_state(volume_name, "detached")

        volume = self.get(volume_name)
        engine = volume.controllers[0]
        assert engine.lastRestoredBackup == ""
        assert engine.requestedBackupRestore == ""

    def create_persistentvolume(self, volume_name, retry):
        for _ in range(self.retry_count):
            try:
                volume = self.get(volume_name)
                if hasattr(volume, 'pvCreate'):
                    break
            except Exception as e:
                logging(f"Failed to get pvCreate method for volume {volume_name}: {e}")
            time.sleep(self.retry_interval)
        else:
            raise AttributeError
        volume.pvCreate(pvName=volume_name, fsType="ext4")

        if not retry:
            return

        created = False
        for _ in range(self.retry_count):
            if self.pv.is_exist(volume_name):
                created = True
                break
            time.sleep(self.retry_interval)
        assert created

    def create_persistentvolumeclaim(self, volume_name, retry):
        for _ in range(self.retry_count):
            try:
                volume = self.get(volume_name)
                if hasattr(volume, 'pvcCreate'):
                    break
            except Exception as e:
                logging(f"Failed to get pvcCreate method for volume {volume_name}: {e}")
            time.sleep(self.retry_interval)
        else:
            raise AttributeError
        volume.pvcCreate(namespace="default", pvcName=volume_name)

        if not retry:
            return

        created = False
        for _ in range(self.retry_count):
            if self.pvc.is_exist(volume_name, namespace="default"):
                created = True
                break
            time.sleep(self.retry_interval)
        assert created

    def upgrade_engine_image(self, volume_name, engine_image_name):
        logging(f"Upgrading volume {volume_name} engine image to {engine_image_name}")
        volume = self.get(volume_name)
        volume.engineUpgrade(image=engine_image_name)

    def wait_for_engine_image_upgrade_completed(self, volume_name, engine_image_name):
        for i in range(self.retry_count):
            logging(f"Waiting for volume {volume_name} engine image to be upgraded to {engine_image_name} ... ({i})")
            volume = self.get(volume_name)
            if volume.currentImage == engine_image_name:
                break
            time.sleep(self.retry_interval)
        assert volume.currentImage == engine_image_name, f"Failed to upgrade engine image to {engine_image_name}: {volume}"
        logging(f"Upgraded volume {volume_name} engine image to {engine_image_name}")

    def wait_for_replica_ready_to_rw(self, volume_name):
        for i in range(self.retry_count):
            ready = True
            volume = self.get(volume_name)
            replicas = volume.replicas
            logging(f"Waiting for volume {volume_name} replica count = {volume.numberOfReplicas}, current count = {len(replicas)} ... ({i})")
            if len(replicas) != volume.numberOfReplicas:
                ready = False
                time.sleep(self.retry_interval)
                continue
            else:
                for replica in replicas:
                    if replica.mode != "RW":
                        ready = False
                        break
            if ready:
                break
            time.sleep(self.retry_interval)
        assert ready, f"Failed to get volume {volume_name} replicas ready: {replicas}"

    def trim_filesystem(self, volume_name, is_expect_fail=False):
        is_unexpected_pass = False
        try:
            self.get(volume_name).trimFilesystem(name=volume_name)

            if is_expect_fail:
                is_unexpected_pass = True

        except Exception as e:
            if is_expect_fail:
                logging(f"Failed to trim filesystem: {e}")
            else:
                raise e

        if is_unexpected_pass:
            raise Exception(f"Expected volume {volume_name} trim filesystem to fail")

    def update_offline_replica_rebuild(self, volume_name, rebuild_type):
        volume = self.get(volume_name)
        volume.offlineReplicaRebuilding(OfflineRebuilding=rebuild_type)

    def update_data_locality(self, volume_name, data_locality):
        volume = self.get(volume_name)
        volume.updateDataLocality(dataLocality=data_locality)
