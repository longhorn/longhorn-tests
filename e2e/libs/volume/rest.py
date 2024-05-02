import os
import time
import asyncio
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
        self.longhorn_client = get_longhorn_client()
        self.node_exec = node_exec
        self.retry_count, self.retry_interval = get_retry_count_and_interval()

    def get(self, volume_name):
        for i in range(self.retry_count):
            try:
                return self.longhorn_client.by_id_volume(volume_name)
            except Exception as e:
                logging(f"Failed to get volume {volume_name} with error: {e}")
            time.sleep(self.retry_interval)

    def create(self, volume_name, size, replica_count):
        return NotImplemented

    def attach(self, volume_name, node_name):
        return NotImplemented

    def detach(self, volume_name, node_name):
        return NotImplemented

    def delete(self, volume_name):
        return NotImplemented

    def wait_for_volume_state(self, volume_name, desired_state):
        return NotImplemented

    def wait_for_volume_migration_ready(self, volume_name):
        return NotImplemented

    def wait_for_volume_migration_completed(self, volume_name, node_name):
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
                    v = self.longhorn_client.by_id_volume(volume_name)
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

    def write_random_data(self, volume_name, size):
        return NotImplemented

    def keep_writing_data(self, volume_name, size):
        return NotImplemented

    def delete_replica(self, volume_name, node_name):
        return NotImplemented

    async def wait_for_replica_rebuilding_start(self, volume_name, node_name):
        rebuilding_replica_name = None
        for i in range(self.retry_count):
            try:
                v = self.longhorn_client.by_id_volume(volume_name)
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
                v = self.longhorn_client.by_id_volume(volume_name)
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
                v = self.longhorn_client.by_id_volume(volume_name)
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
        volume = self.longhorn_client.by_id_volume(volume_name)
        for r in volume.replicas:
            replica_map[r.instanceManagerName] = r.name

        for rm_name, r_name in replica_map.items():
            delete_command = 'longhorn-instance-manager process delete ' + \
                         '--name ' + r_name
            pod_exec(rm_name, LONGHORN_NAMESPACE, delete_command)

    def wait_for_replica_rebuilding_complete(self, volume_name, node_name):
        completed = False
        for i in range(self.retry_count):
            try:
                v = self.longhorn_client.by_id_volume(volume_name)
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

    def check_data_checksum(self, volume_name, checksum):
        return NotImplemented

    def cleanup(self, volume_names):
        return NotImplemented
