import time

from service.service import is_services_headless

from sharemanager import ShareManager
from sharemanager.constant import LABEL_SHAREMANAGER

from utility.utility import get_retry_count_and_interval
from utility.utility import logging
from utility.utility import get_pod, delete_pod
import utility.constant as constant

class sharemanager_keywords:

    def __init__(self):
        self.sharemanager = ShareManager()

    def is_sharemanagers_using_headless_service(self):
        not_headless_services = []
        sharemanagers = self.sharemanager.list()
        for sharemanager in sharemanagers['items']:
            sharemanager_name = sharemanager['metadata']['name']
            label_selector = f"{LABEL_SHAREMANAGER}={sharemanager_name}"
            if not is_services_headless(label_selector=label_selector):
                not_headless_services.append(sharemanager_name)

        if len(not_headless_services) == 0:
            return True

        return False

    def wait_for_sharemanagers_deleted(self, name=[]):
        retry_count, retry_interval = get_retry_count_and_interval()
        for i in range(retry_count):
            sharemanagers = self.sharemanager.list()

            try:
                if len(name) == 0:
                    assert sharemanagers is None or len(sharemanagers['items']) == 0
                else:
                    for sharemanager in sharemanagers['items']:
                        assert sharemanager['metadata']['name'] not in name

                return

            except AssertionError as e:
                logging(f"Waiting for sharemanager deleted: {e}, retry ({i}) ...")
                time.sleep(retry_interval)

        assert AssertionError, f"Failed to wait for all sharemanagers to be deleted"


    def delete_sharemanager_pod_and_wait_for_recreation(self, name):
        sharemanager_pod_name = "share-manager-" + name
        sharemanager_pod = get_pod(sharemanager_pod_name, constant.LONGHORN_NAMESPACE)
        last_creation_time = sharemanager_pod.metadata.creation_timestamp
        delete_pod(sharemanager_pod_name, constant.LONGHORN_NAMESPACE)

        retry_count, retry_interval = get_retry_count_and_interval()
        for i in range(retry_count):
            time.sleep(retry_interval)
            sharemanager_pod = get_pod(sharemanager_pod_name, constant.LONGHORN_NAMESPACE)
            if sharemanager_pod == None:
                continue
            creation_time = sharemanager_pod.metadata.creation_timestamp
            if creation_time > last_creation_time:
                return

        assert False, f"sharemanager pod {sharemanager_pod_name} not recreated"

    def wait_for_sharemanager_pod_restart(self, name):
        sharemanager_pod_name = "share-manager-" + name
        sharemanager_pod = get_pod(sharemanager_pod_name, constant.LONGHORN_NAMESPACE)
        last_creation_time = sharemanager_pod.metadata.creation_timestamp

        retry_count, retry_interval = get_retry_count_and_interval()
        for i in range(retry_count):
            logging(f"Waiting for sharemanager for volume {name} restart ... ({i})")
            time.sleep(retry_interval)
            sharemanager_pod = get_pod(sharemanager_pod_name, constant.LONGHORN_NAMESPACE)
            if sharemanager_pod == None:
                continue
            creation_time = sharemanager_pod.metadata.creation_timestamp
            logging(f"Getting new sharemanager which is created at {creation_time}, and old one is created at {last_creation_time}")
            if creation_time > last_creation_time:
                return

        assert False, f"sharemanager pod {sharemanager_pod_name} isn't restarted"


    def wait_for_share_manager_pod_running(self, name):
        sharemanager_pod_name = "share-manager-" + name
        retry_count, retry_interval = get_retry_count_and_interval()
        for i in range(retry_count):
            sharemanager_pod = get_pod(sharemanager_pod_name, constant.LONGHORN_NAMESPACE)
            logging(f"Waiting for sharemanager for volume {name} running, currently {sharemanager_pod.status.phase} ... ({i})")
            if sharemanager_pod.status.phase == "Running":
                return

        assert False, f"sharemanager pod {sharemanager_pod_name} not running"
