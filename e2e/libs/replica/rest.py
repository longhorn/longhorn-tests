import time

from replica.base import Base
from replica.constant import RETRY_COUNTS
from replica.constant import RETRY_INTERVAL

from utility.utility import logging
from utility.utility import get_longhorn_client


class Rest(Base):
    def __init__(self, node_exec):
        self.node_exec = node_exec

    def get_replica(self, volume_name, node_name):
        return NotImplemented

    def delete_replica(self, volume_name, node_name):
        return NotImplemented

    def wait_for_replica_rebuilding_start(self, volume_name, node_name):
        rebuilding_replica_name = None
        for i in range(RETRY_COUNTS):
            try:
                v = get_longhorn_client().by_id_volume(volume_name)
                for replica in v.replicas:
                    if replica.hostId == node_name:
                        rebuilding_replica_name = replica.name
                        break
                if rebuilding_replica_name:
                    break
            except Exception as e:
                logging(f"Failed to get volume {volume_name} with error: {e}")
            time.sleep(RETRY_INTERVAL)
        assert rebuilding_replica_name != None, f'failed to get rebuilding replica name'

        started = False
        for i in range(RETRY_COUNTS):
            try:
                v = get_longhorn_client().by_id_volume(volume_name)
                for status in v.rebuildStatus:
                    if status.replica == rebuilding_replica_name and\
                       status.state == "in_progress":
                        started = True
                        break
                if started:
                    break
            except Exception as e:
                logging(f"Failed to get volume {volume_name} with error: {e}")
            time.sleep(RETRY_INTERVAL)
        assert started, f'replica {rebuilding_replica_name} rebuilding starting failed'

    def wait_for_replica_rebuilding_complete(self, volume_name, node_name):
        completed = False
        for i in range(RETRY_COUNTS):
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
            except Exception as e:
                logging(f"Failed to get volume {volume_name} with error: {e}")
            if completed:
                break
            time.sleep(RETRY_INTERVAL)
        assert completed, f'failed rebuilding replicas'
