import time

from service.service import is_services_headless

from sharemanager import ShareManager
from sharemanager.constant import LABEL_SHAREMANAGER

from utility.utility import get_retry_count_and_interval
from utility.utility import logging
from utility.utility import get_pod, delete_pod

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
        sharemanager_pod = get_pod(sharemanager_pod_name, "longhorn-system")
        last_creation_time = sharemanager_pod.metadata.creation_timestamp
        delete_pod(sharemanager_pod_name, "longhorn-system")

        retry_count, retry_interval = get_retry_count_and_interval()
        for i in range(retry_count):
            time.sleep(retry_interval)
            sharemanager_pod = get_pod(sharemanager_pod_name, "longhorn-system")
            if sharemanager_pod == None:
                continue
            creation_time = sharemanager_pod.metadata.creation_timestamp
            if creation_time > last_creation_time:
                return

        assert False, f"sharemanager pod {sharemanager_pod_name} not recreated"

    def wait_for_sharemanager_pod_restart(self, name):
        sharemanager_pod_name = "share-manager-" + name
        sharemanager_pod = get_pod(sharemanager_pod_name, "longhorn-system")
        last_creation_time = sharemanager_pod.metadata.creation_timestamp

        retry_count, retry_interval = get_retry_count_and_interval()
        for i in range(retry_count):
            logging(f"Waiting for sharemanager for volume {name} restart ... ({i})")
            time.sleep(retry_interval)
            sharemanager_pod = get_pod(sharemanager_pod_name, "longhorn-system")
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
            sharemanager_pod = get_pod(sharemanager_pod_name, "longhorn-system")
            logging(f"Waiting for sharemanager for volume {name} running, currently {sharemanager_pod.status.phase} ... ({i})")
            if sharemanager_pod.status.phase == "Running":
                return

        assert False, f"sharemanager pod {sharemanager_pod_name} not running"

    def wait_for_disk_size_in_sharemanager_pod(self, share_manager_pod, volume_name, expected_size):
        from utility.utility import pod_exec
        retry_count, retry_interval = get_retry_count_and_interval()
        for i in range(retry_count):
            logging(f"Waiting for disk size in sharemanager pod {share_manager_pod} to be {expected_size} ... ({i})")
            time.sleep(retry_interval)
            cmd = f"df -B1 /export/{volume_name} | tail -1 | awk '{{print $2}}'"
            try:
                result = pod_exec(share_manager_pod, "longhorn-system", cmd)
                actual_size = result.strip()
                logging(f"Current disk size in sharemanager pod {share_manager_pod}: {actual_size}, expected: {expected_size}")
                if actual_size == expected_size:
                    return
            except Exception as e:
                logging(f"Error checking disk size in sharemanager pod {share_manager_pod}: {e}")
                continue

        assert False, f"Disk size in sharemanager pod {share_manager_pod} is not {expected_size}"

    def wait_for_encrypted_disk_size_in_sharemanager_pod(self, share_manager_pod, volume_name, expected_size):
        from utility.utility import pod_exec
        retry_count, retry_interval = get_retry_count_and_interval()
        for i in range(retry_count):
            logging(f"Waiting for encrypted disk size in sharemanager pod {share_manager_pod} to be {expected_size} ... ({i})")
            time.sleep(retry_interval)
            cmd = f"fdisk -l | grep /dev/mapper/{volume_name}"
            try:
                result = pod_exec(share_manager_pod, "longhorn-system", cmd)
                logging(f"Current encrypted disk info in sharemanager pod {share_manager_pod}: {result}")
                if expected_size in result:
                    return
            except Exception as e:
                logging(f"Error checking encrypted disk size in sharemanager pod {share_manager_pod}: {e}")
                continue

        assert False, f"Encrypted disk size in sharemanager pod {share_manager_pod} does not contain {expected_size}"
