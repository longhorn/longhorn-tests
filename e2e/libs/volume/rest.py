import time
import os

from volume.base import Base
from utils import common_utils

RETRY_COUNTS = 150
RETRY_INTERVAL = 1

VOLUME_FRONTEND_BLOCKDEV = "blockdev"
VOLUME_FRONTEND_ISCSI = "iscsi"
DEV_PATH = "/dev/longhorn/"


class Rest(Base):

    def __init__(self, node_exec):
        self.longhorn_client = common_utils.get_longhorn_client()
        self.node_exec = node_exec

    def create(self, volume_name, size, replica_count, volume_type):
        return NotImplemented

    def create_with_manifest(self, manifest):
        return NotImplemented

    def get(self, volume_name):
        return self.longhorn_client.by_id_volume(volume_name)

    def delete(self, volume_name=""):
        return NotImplemented

    def attach(self, volume_name, node_name):
        return NotImplemented

    def wait_for_volume_state(self, volume_name, desired_state):
        return NotImplemented

    def get_volume_state(self, volume_name):
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

        if v.frontend == VOLUME_FRONTEND_BLOCKDEV:
            assert endpoint == os.path.join(DEV_PATH, v.name)
        elif v.frontend == VOLUME_FRONTEND_ISCSI:
            assert endpoint.startswith("iscsi://")

        return endpoint

    def write_random_data(self, volume_name, size):
        return NotImplemented

    def check_data(self, volume_name, checksum):
        return NotImplemented
