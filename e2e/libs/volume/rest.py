import os
import time
import asyncio

from node_exec.constant import HOST_ROOTFS

from persistentvolumeclaim.persistentvolumeclaim import PersistentVolumeClaim
from persistentvolume.persistentvolume import PersistentVolume

from volume.base import Base
from volume.constant import DEV_PATH
from volume.constant import VOLUME_FRONTEND_BLOCKDEV
from volume.constant import VOLUME_FRONTEND_ISCSI

from utility.constant import LONGHORN_NAMESPACE
from utility.utility import get_retry_count_and_interval
from utility.utility import get_longhorn_client
from utility.utility import logging
from utility.utility import pod_exec


class Rest(Base):

    def __init__(self, node_exec):
        self.node_exec = node_exec
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

    def create(self, volume_name, size, numberOfReplicas, frontend, migratable, accessMode, dataEngine, backingImage, Standby, fromBackup):
        return NotImplemented

    def attach(self, volume_name, node_name, disable_frontend):
        return NotImplemented

    def detach(self, volume_name, node_name):
        return NotImplemented

    def delete(self, volume_name):
        return NotImplemented

    def wait_for_volume_state(self, volume_name, desired_state):
        for i in range(self.retry_count):
            volume = self.get(volume_name)
            if volume['state'] == desired_state:
                break
            time.sleep(self.retry_interval)
        assert volume['state'] == desired_state

    def wait_for_volume_migration_ready(self, volume_name):
        return NotImplemented

    def wait_for_volume_migration_completed(self, volume_name, node_name):
        return NotImplemented

    def wait_for_volume_restoration_completed(self, volume_name):
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

    async def wait_for_replica_rebuilding_start(self, volume_name, node_name):
        rebuilding_replica_name = None
        for i in range(self.retry_count):
            try:
                v = get_longhorn_client().by_id_volume(volume_name)
                logging(f"Trying to get volume {volume_name} rebuilding replicas ... ({i})")
                for replica in v.replicas:
                    if replica.hostId == node_name:
                        rebuilding_replica_name = replica.name
                        break
                if rebuilding_replica_name:
                    break
            except Exception as e:
                logging(f"Failed to get volume {volume_name} with error: {e}")
            await asyncio.sleep(self.retry_interval)
        assert rebuilding_replica_name != None
        logging(f"Got volume {volume_name} rebuilding replica = {rebuilding_replica_name} on node {node_name}")

        started = False
        for i in range(self.retry_count):
            try:
                v = get_longhorn_client().by_id_volume(volume_name)
                logging(f"Got volume {volume_name} rebuild status = {v.rebuildStatus}")
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

    def is_replica_rebuilding_in_progress(self, volume_name, node_name):
        in_progress = False
        for i in range(self.retry_count):
            try:
                v = get_longhorn_client().by_id_volume(volume_name)
                logging(f"Got volume {volume_name} rebuild status = {v.rebuildStatus}")
                for status in v.rebuildStatus:
                    for replica in v.replicas:
                        if status.replica == replica.name and \
                           replica.hostId == node_name and \
                           status.state == "in_progress":
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
            pod_exec(rm_name, LONGHORN_NAMESPACE, delete_command)

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
                pod_exec(rm_name, LONGHORN_NAMESPACE, delete_command)

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

    def wait_for_replica_rebuilding_complete(self, volume_name, node_name):
        completed = False
        for i in range(self.retry_count):
            try:
                v = get_longhorn_client().by_id_volume(volume_name)
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
                if completed:
                    break
            except Exception as e:
                logging(f"Failed to get volume {volume_name} with error: {e}")
            time.sleep(self.retry_interval)
        logging(f"Completed volume {volume_name} replica rebuilding on {node_name}")
        assert completed, f"Expect volume {volume_name} replica rebuilding completed"

    def check_data_checksum(self, volume_name, data_id):
        return NotImplemented

    def get_checksum(self, volume_name):
        node_name = self.get(volume_name).controllers[0].hostId
        endpoint = self.get_endpoint(volume_name)
        checksum = self.node_exec.issue_cmd(
            node_name,
            ["sh", "-c", f"md5sum {endpoint} | awk \'{{print $1}}\'"])
        logging(f"Calculated volume {volume_name} checksum {checksum}")
        return checksum

    def cleanup(self, volume_names):
        return NotImplemented

    def update_volume_spec(self, volume_name, key, value):
        return NotImplemented

    def activate(self, volume_name):
        for _ in range(self.retry_count):
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
                assert "hasn't finished incremental restored" in str(e.error.message)
                time.sleep(RETRY_INTERVAL)
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
        self.get(volume_name).pvCreate(pvName=volume_name, fsType="ext4")

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
        self.get(volume_name).pvcCreate(namespace="default", pvcName=volume_name)

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
        volume = self.get(volume_name)
        volume.engineUpgrade(image=engine_image_name)

    def wait_for_engine_image_upgrade_completed(self, volume_name, engine_image_name):
        for i in range(self.retry_count):
            volume = self.get(volume_name)
            if volume.currentImage == engine_image_name:
                break
            time.sleep(self.retry_interval)
        assert volume.currentImage == engine_image_name, f"Failed to upgrade engine image to {engine_image_name}: {volume}"
        self.wait_for_replica_ready_to_rw(volume_name)

    def wait_for_replica_ready_to_rw(self, volume_name):
        for _ in range(self.retry_count):
            ready = True
            volume = self.get(volume_name)
            replicas = volume.replicas
            if len(replicas) != volume.numberOfReplicas:
                logging(f"Waiting for volume {volume_name} replica count = {volume.numberOfReplicas}, current count = {len(replicas)}")
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
