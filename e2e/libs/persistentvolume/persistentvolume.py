import time
import yaml

from kubernetes import client
from kubernetes.client.rest import ApiException

from utility.constant import LABEL_TEST
from utility.constant import LABEL_TEST_VALUE
from utility.utility import get_retry_count_and_interval
from utility.utility import logging


class PersistentVolume():

    def __init__(self):
        self.api = client.CoreV1Api()
        self.retry_count, self.retry_interval = get_retry_count_and_interval()

    def create(self, name, storage, volume_mode="Filesystem", fsType="ext4"):
        filepath = "./templates/workload/pv.yaml"
        with open(filepath, 'r') as f:
            manifest_dict = yaml.safe_load(f)

            manifest_dict['metadata']['name'] = name
            manifest_dict['metadata']['labels'][LABEL_TEST] = LABEL_TEST_VALUE
            manifest_dict['spec']['capacity']['storage'] = storage
            manifest_dict['spec']['volumeMode'] = volume_mode
            manifest_dict['spec']['csi']['fsType'] = fsType
            manifest_dict['spec']['csi']['volumeHandle'] = name

            logging(f"yaml = {manifest_dict}")

            self.api.create_persistent_volume(body=manifest_dict)

        created = False
        for _ in range(self.retry_count):
            if self.is_exist(name):
                created = True
                break
            time.sleep(self.retry_interval)
        assert created, f"Failed to create PV {name}"

    def delete(self, name):
        try:
            self.api.delete_persistent_volume(
                name=name,
                grace_period_seconds=0)
        except ApiException as e:
            assert e.status == 404

        deleted = False
        for _ in range(self.retry_count):
            if not self.is_exist(name):
                deleted = True
                break
            time.sleep(self.retry_interval)
        assert deleted

    def is_exist(self, name):
        resp = self.api.list_persistent_volume()
        exist = False
        for item in resp.items:
            if item.metadata.name == name:
                exist = True
                break
        return exist
