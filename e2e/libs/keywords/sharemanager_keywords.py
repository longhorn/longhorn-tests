import time

from service.service import is_services_headless

from sharemanager import ShareManager
from sharemanager.constant import LABEL_SHAREMANAGER

from utility.utility import get_retry_count_and_interval
from utility.utility import logging


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

    def delete_sharemanager(self, name):
        return self.sharemanager.delete(name)

    def delete_sharemanager_and_wait_for_recreation(self, name):        
        sharemanager = self.sharemanager.get(name)
        last_creation_time = sharemanager["metadata"]["creationTimestamp"]        
        self.sharemanager.delete(name)
        self.sharemanager.wait_for_restart(name, last_creation_time)

    def wait_for_share_manager_running(self, name):
        return self.sharemanager.wait_for_running(name)
