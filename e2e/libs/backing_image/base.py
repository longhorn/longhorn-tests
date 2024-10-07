from abc import ABC, abstractmethod


class Base(ABC):

    BACKING_IMAGE_SOURCE_TYPE_DOWNLOAD = "download"
    BACKING_IMAGE_SOURCE_TYPE_FROM_VOLUME = "export-from-volume"
    BACKING_IMAGE_STATE_READY = "ready"

    @abstractmethod
    def create(self, bi_name, source_type, url, expected_checksum):
        return NotImplemented

    @abstractmethod
    def get(self, bi_name):
        return NotImplemented

    @abstractmethod
    def all_disk_file_status_are_ready(self, bi_name):
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
