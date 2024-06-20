import time
from kubernetes import client
from kubernetes.client.rest import ApiException
from utility.utility import get_retry_count_and_interval
from utility.utility import logging


class PersistentVolume():

    def __init__(self):
        self.api = client.CoreV1Api()
        self.retry_count, self.retry_interval = get_retry_count_and_interval()

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
