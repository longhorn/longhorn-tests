from kubernetes import client
from datetime import datetime
from backing_image.base import Base

from utility.utility import logging
from utility.utility import get_retry_count_and_interval
import time

class CRD(Base):
    def __init__(self):
        self.obj_api = client.CustomObjectsApi()
        self.retry_count, self.retry_interval = get_retry_count_and_interval()
        
    def create(self, bi_name, source_type, url, expected_checksum):
        return NotImplemented

    def get(self, bi_name):
        return NotImplemented

    def all_disk_file_status_are_ready(self, bi_name):
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
            namespace="longhorn-system",
            plural="backingimagemanagers",
            label_selector=label_selector)
    
    def delete_backing_image_manager(self, name):
        logging(f"deleting backing image manager {name} ...")
        self.obj_api.delete_namespaced_custom_object(
            group="longhorn.io",
            version="v1beta2",
            namespace="longhorn-system",
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
                logging(f"backing image mamager {name} currently in {current_state} state")
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
                    namespace="longhorn-system",
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
