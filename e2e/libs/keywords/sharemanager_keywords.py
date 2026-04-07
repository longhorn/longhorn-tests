import time

from sharemanager import ShareManager

from service.service import list_services
from event.event import get_events
from utility.utility import get_retry_count_and_interval
from utility.utility import logging
from utility.utility import get_pod, delete_pod, pod_exec, wait_delete_pod
import utility.constant as constant

class sharemanager_keywords:

    def __init__(self):
        self.sharemanager = ShareManager()
        self.retry_count, self.retry_interval = get_retry_count_and_interval()

    def is_sharemanagers_using_headless_service(self):
        LABEL_SHAREMANAGER = "longhorn.io/share-manager"
        headless_services = []
        sharemanagers = self.sharemanager.list()
        for sharemanager in sharemanagers:
            # the sharemanager pod has a label longhorn.io/share-manager=volume-name,
            # and the headless service also has the same label,
            # so we can find the headless service by the label selector
            volume_name = sharemanager['metadata']['labels'][LABEL_SHAREMANAGER]
            label_selector = f"{LABEL_SHAREMANAGER}={volume_name}"
            services = list_services(label_selector)
            for service in services:
                if service['spec']['clusterIP'] == "None":
                    headless_services.append(volume_name)
        if len(headless_services):
            return True
        else:
            return False

    def wait_for_sharemanagers_deleted(self):
        sharemanagers = self.sharemanager.list()
        for sharemanager in sharemanagers:
            logging(f"Waiting for sharemanager {sharemanager['metadata']['name']} deletion ...")
            wait_delete_pod(sharemanager['metadata']['name'], constant.LONGHORN_NAMESPACE)

    def delete_sharemanager_pod(self, name):
        sharemanager_pod_name = "share-manager-" + name
        self.sharemanager.delete(sharemanager_pod_name)

    def wait_for_sharemanager_pod_deleted(self, volume_name):
        sharemanager_pod_name = "share-manager-" + volume_name
        logging(f"Waiting for sharemanager pod {sharemanager_pod_name} to be deleted ...")
        wait_delete_pod(sharemanager_pod_name, constant.LONGHORN_NAMESPACE)

    def wait_for_sharemanager_pod_recreation(self, name):
        sharemanager_pod_name = "share-manager-" + name
        for i in range(self.retry_count):
            try:
                logging(f"Waiting for sharemanager {sharemanager_pod_name} for volume {name} recreation ... ({i})")
                events = get_events()
                scheduled_event_found = False
                killing_event_found = False
                for event in events:
                    reason = event.get('reason')
                    obj_name = event.get('involvedObject', {}).get('name')
                    if obj_name == sharemanager_pod_name and (reason == "Scheduled" or reason == "Created"):
                        logging(f"Found new sharemanager {sharemanager_pod_name} for volume {name} is recreated")
                        scheduled_event_found = True
                    if obj_name == sharemanager_pod_name and (reason == "Killing" or reason == "NodeNotReady"):
                        logging(f"Found old sharemanager {sharemanager_pod_name} for volume {name} was replaced")
                        killing_event_found = True
                if scheduled_event_found and killing_event_found:
                    return
            except Exception as e:
                logging(f"Waiting for sharemanager {sharemanager_pod_name} for volume {name} recreation error: {e}")
            time.sleep(self.retry_interval)

        assert False, f"Failed to wait for sharemanager pod {sharemanager_pod_name} recreation: {events}"

    def check_no_sharemanager_pod_recreation(self, name):
        sharemanager_pod_name = "share-manager-" + name
        logging(f"Checking no sharemanager {sharemanager_pod_name} for volume {name} recreation")
        events = get_events()
        scheduled_event_found = False
        killing_event_found = False
        for event in events:
            reason = event.get('reason')
            obj_name = event.get('involvedObject', {}).get('name')
            if obj_name == sharemanager_pod_name and (reason == "Scheduled" or reason == "Created"):
                scheduled_event_found = True
            if obj_name == sharemanager_pod_name and reason == "Killing":
                killing_event_found = True
        if scheduled_event_found and killing_event_found:
            logging(f"Unexpected sharemanager {sharemanager_pod_name} for volume {name} recreation: {events}")
            time.sleep(self.retry_count)
            assert False, f"Unexpected sharemanager pod {sharemanager_pod_name} recreation: {events}"

    def wait_for_share_manager_pod_running(self, name):
        sharemanager_pod_name = "share-manager-" + name
        for i in range(self.retry_count):
            try:
                sharemanager_pod = self.sharemanager.get(sharemanager_pod_name)
                logging(f"Waiting for sharemanager for volume {name} running, currently {sharemanager_pod.status.phase} ... ({i})")
                if sharemanager_pod.status.phase == "Running":
                    return sharemanager_pod.metadata.creation_timestamp
            except Exception as e:
                logging(f"Waiting for sharemanager for volume {name} running error: {e}")
            time.sleep(self.retry_interval)

        assert False, f"sharemanager pod {sharemanager_pod_name} not running"

    def wait_for_disk_size_in_sharemanager_pod(self, share_manager_pod, volume_name, expected_size):
        for i in range(self.retry_count):
            logging(f"Waiting for disk size in sharemanager pod {share_manager_pod} to be {expected_size} ... ({i})")
            time.sleep(self.retry_interval)
            cmd = f"blockdev --getsize64 /dev/longhorn/{volume_name}"
            try:
                result = pod_exec(share_manager_pod, constant.LONGHORN_NAMESPACE, cmd)
                actual_size = result.strip()
                logging(f"Current disk size in sharemanager pod {share_manager_pod}: {actual_size}, expected: {expected_size}")
                if actual_size == expected_size:
                    return
            except Exception as e:
                logging(f"Error checking disk size in sharemanager pod {share_manager_pod}: {e}")
                continue

        assert False, f"Disk size in sharemanager pod {share_manager_pod} is not {expected_size}"

    def wait_for_encrypted_disk_size_in_sharemanager_pod(self, share_manager_pod, volume_name, expected_size):
        for i in range(self.retry_count):
            logging(f"Waiting for encrypted disk size in sharemanager pod {share_manager_pod} to be {expected_size} ... ({i})")
            time.sleep(self.retry_interval)
            cmd = f"fdisk -l | grep /dev/mapper/{volume_name}"
            try:
                result = pod_exec(share_manager_pod, constant.LONGHORN_NAMESPACE, cmd)
                logging(f"Current encrypted disk info in sharemanager pod {share_manager_pod}: {result}")
                if expected_size in result:
                    return
            except Exception as e:
                logging(f"Error checking encrypted disk size in sharemanager pod {share_manager_pod}: {e}")
                continue

        assert False, f"Encrypted disk size in sharemanager pod {share_manager_pod} does not contain {expected_size}"

    def get_sharemanager_spec_image(self, volume_name):
        return self.sharemanager.get_spec_image(volume_name)

    def get_sharemanager_current_image(self, volume_name):
        return self.sharemanager.get_status_current_image(volume_name)

    def get_sharemanager_pod_container_image(self, volume_name):
        return self.sharemanager.get_pod_container_image(volume_name)
