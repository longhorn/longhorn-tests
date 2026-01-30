import time

from datetime import datetime
from kubernetes import client

from backing_image.base import Base

from utility.utility import logging
from utility.utility import get_retry_count_and_interval
import utility.constant as constant


class CRD(Base):
    def __init__(self):
        self.obj_api = client.CustomObjectsApi()
        self.retry_count, self.retry_interval = get_retry_count_and_interval()

    def create(self, name, sourceType, url, expectedChecksum, dataEngine, minNumberOfCopies):
        return NotImplemented

    def get(self, bi_name):
        return NotImplemented

    def all_disk_file_status_are_ready(self, bi_name):
        return NotImplemented

    def disk_file_status_match_expected(self, bi_name, expected_ready_count, expected_unknown_count):
        return NotImplemented

    def wait_for_disk_file_status_match_expected(self, bi_name, expected_ready_count, expected_unknown_count):
        return NotImplemented

    def clean_up_backing_image_from_a_random_disk(self, bi_name):
        return NotImplemented

    def delete(self, bi_name):
        return NotImplemented

    def wait_for_backing_image_disk_cleanup(self, bi_name, disk_id):
        return NotImplemented

    def wait_for_backing_image_delete(self, bi_name):
        return NotImplemented

    def cleanup_backing_images(self):
        return NotImplemented

    def list_backing_image_manager(self):
        label_selector = 'longhorn.io/component=backing-image-manager'
        return self.obj_api.list_namespaced_custom_object(
            group="longhorn.io",
            version="v1beta2",
            namespace=constant.LONGHORN_NAMESPACE,
            plural="backingimagemanagers",
            label_selector=label_selector)

    def delete_backing_image_manager(self, name):
        logging(f"deleting backing image manager {name} ...")
        self.obj_api.delete_namespaced_custom_object(
            group="longhorn.io",
            version="v1beta2",
            namespace=constant.LONGHORN_NAMESPACE,
            plural="backingimagemanagers",
            name=name
        )

    def wait_all_backing_image_managers_running(self):
        for i in range(self.retry_count):
            all_running = True
            backing_image_managers = self.list_backing_image_manager()
            for backing_image_manager in backing_image_managers["items"]:
                current_state = backing_image_manager["status"]["currentState"]
                name = backing_image_manager["metadata"]["name"]
                logging(f"backing image manager {name} currently in {current_state} state")
                if current_state != "running":
                    all_running = False
            if all_running is True:
                return
            time.sleep(self.retry_interval)
        assert False, f"Waiting all backing image manager in running state timeout"

    def wait_backing_image_manager_restart(self, name, last_creation_time):
        for i in range(self.retry_count):
            time.sleep(self.retry_interval)
            try:
                backing_image_manager = self.obj_api.get_namespaced_custom_object(
                    group="longhorn.io",
                    version="v1beta2",
                    namespace=constant.LONGHORN_NAMESPACE,
                    plural="backingimagemanagers",
                    name=name
                    )
            except Exception as e:
                logging(f"Finding backing image manager {name} failed with error {e}")
                continue

            creation_time = backing_image_manager["metadata"]["creationTimestamp"]
            fmt = "%Y-%m-%dT%H:%M:%SZ"
            if datetime.strptime(creation_time, fmt) > datetime.strptime(last_creation_time, fmt):
                return

        assert False, f"Wait backing image manager {name} restart failed ..."

    def wait_all_disk_file_status_are_at_state(self, bi_name, expected_state):
        return NotImplemented

    def check_disk_file_map_contain_specific_message(self, bi_name, expected_message):
        return NotImplemented
