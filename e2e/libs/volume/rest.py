from volume.base import Base
from utility.utility import get_longhorn_client
from utility.utility import logging
import time
import os

RETRY_COUNTS = 150
RETRY_INTERVAL = 1

VOLUME_FRONTEND_BLOCKDEV = "blockdev"
VOLUME_FRONTEND_ISCSI = "iscsi"
DEV_PATH = "/dev/longhorn/"

class Rest(Base):

    def __init__(self, node_exec):
        self.longhorn_client = get_longhorn_client()
        self.node_exec = node_exec

    def get(self, volume_name):
        return self.longhorn_client.by_id_volume(volume_name)

    def create(self, volume_name, size, replica_count):
        return NotImplemented

    def attach(self, volume_name, node_name):
        return NotImplemented

    def delete(self, volume_name):
        return NotImplemented

    def wait_for_volume_state(self, volume_name, desired_state):
        return NotImplemented

    def get_endpoint(self, volume_name):
        endpoint = ""
        v = self.longhorn_client.by_id_volume(volume_name)
        if v.disableFrontend:
            assert endpoint == ""
            return endpoint
        else:
            assert v.frontend == VOLUME_FRONTEND_BLOCKDEV or\
                   v.frontend == VOLUME_FRONTEND_ISCSI
            for i in range(RETRY_COUNTS):
                v = self.longhorn_client.by_id_volume(volume_name)
                engines = v.controllers
                assert len(engines) != 0
                endpoint = engines[0].endpoint
                if endpoint != "":
                    break
                time.sleep(RETRY_INTERVAL)

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

    def wait_for_replica_rebuilding_start(self, volume_name, node_name):
        rebuilding_replica_name = None
        for i in range(RETRY_COUNTS):
            v = self.longhorn_client.by_id_volume(volume_name)
            logging(f"Got volume {volume_name} replicas = {v.replicas}")
            for replica in v.replicas:
                if replica.hostId == node_name:
                    rebuilding_replica_name = replica.name
                    break
            if rebuilding_replica_name:
                break
            time.sleep(RETRY_INTERVAL)
        assert rebuilding_replica_name != None
        logging(f"Got rebuilding replica = {rebuilding_replica_name}")

        started = False
        for i in range(RETRY_COUNTS):
            v = self.longhorn_client.by_id_volume(volume_name)
            logging(f"Got volume rebuild status = {v.rebuildStatus}")
            for status in v.rebuildStatus:
                for replica in v.replicas:
                    if status.replica == replica.name and \
                       replica.hostId == node_name and \
                       status.state == "in_progress":
                       logging(f"Started {node_name}'s replica {replica.name} rebuilding")
                       started = True
                       break
            if started:
                break
            time.sleep(RETRY_INTERVAL)
        assert started, f"wait for replica on node {node_name} rebuilding timeout: {v}"

    def wait_for_replica_rebuilding_complete(self, volume_name, node_name):
        completed = False
        for i in range(RETRY_COUNTS):
            v = self.longhorn_client.by_id_volume(volume_name)
            logging(f"Got volume {volume_name} replicas = {v.replicas}")
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
                    logging(f"Completed {node_name}'s replica {replica.name} rebuilding")
                    completed = True
                    break
            if completed:
                break
            time.sleep(RETRY_INTERVAL)
        assert completed

    def check_data(self, volume_name, checksum):
        return NotImplemented

    def cleanup(self, volume_names):
        return NotImplemented