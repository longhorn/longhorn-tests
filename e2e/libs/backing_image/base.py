from abc import ABC, abstractmethod
from kubernetes import client

class Base(ABC):

    BACKING_IMAGE_SOURCE_TYPE_DOWNLOAD = "download"
    BACKING_IMAGE_SOURCE_TYPE_FROM_VOLUME = "export-from-volume"
    BACKING_IMAGE_STATE_READY = "ready"
    BACKING_IMAGE_STATE_UNKNOWN = "unknown"

    @abstractmethod
    def create(self, name, sourceType, url, expectedChecksum, dataEngine, minNumberOfCopies, wait):
        return NotImplemented

    @abstractmethod
    def get(self, bi_name):
        return NotImplemented

    @abstractmethod
    def all_disk_file_status_are_ready(self, bi_name):
        return NotImplemented

    @abstractmethod
    def disk_file_status_match_expected(self, bi_name, expected_ready_count, expected_unknown_count):
        return NotImplemented

    @abstractmethod
    def wait_for_disk_file_status_match_expected(self, bi_name, expected_ready_count, expected_unknown_count):
        return NotImplemented

    @abstractmethod
    def clean_up_backing_image_from_a_random_disk(self, bi_name):
        return NotImplemented

    @abstractmethod
    def delete(self, bi_name):
        return NotImplemented

    @abstractmethod
    def cleanup_backing_images(self):
        return NotImplemented

    @abstractmethod
    def wait_all_backing_image_managers_running(self):
        return NotImplemented

    @abstractmethod
    def list_backing_image_manager(self):
        return NotImplemented

    @abstractmethod
    def delete_backing_image_manager(self, name):
        return NotImplemented

    @abstractmethod
    def wait_backing_image_manager_restart(self, name, last_creation_time):
        return NotImplemented

    @abstractmethod
    def wait_all_disk_file_status_are_at_state(bi_name, expected_state):
        return NotImplemented

    @abstractmethod
    def check_disk_file_map_contain_specific_message(bi_name, expect_message):
        return NotImplemented
