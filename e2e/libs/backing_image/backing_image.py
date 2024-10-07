from backing_image.base import Base
from backing_image.rest import Rest
from backing_image.crd import CRD
from strategy import LonghornOperationStrategy


class BackingImage(Base):

    _strategy = LonghornOperationStrategy.REST

    def __init__(self):
        if self._strategy == LonghornOperationStrategy.REST:
            self.backing_image = Rest()

    def create(self, bi_name, url, expected_checksum):
        source_type = self.BACKING_IMAGE_SOURCE_TYPE_DOWNLOAD if url else self.BACKING_IMAGE_SOURCE_TYPE_FROM_VOLUME
        return self.backing_image.create(bi_name, source_type, url, expected_checksum)

    def get(self, bi_name):
        return self.backing_image.get(bi_name)

    def all_disk_file_status_are_ready(self, bi_name):
        return self.backing_image.all_disk_file_status_are_ready(bi_name)

    def clean_up_backing_image_from_a_random_disk(self, bi_name):
        return self.backing_image.clean_up_backing_image_from_a_random_disk(bi_name)

    def delete(self, bi_name):
        return self.backing_image.delete(bi_name)

    def cleanup_backing_images(self):
        return self.backing_image.cleanup_backing_images()

    def delete_backing_image_manager(self, name):
        self.backing_image = CRD()
        return self.backing_image.delete_backing_image_manager(name)
    
    def wait_all_backing_image_managers_running(self):
        self.backing_image = CRD()
        return self.backing_image.wait_all_backing_image_managers_running()
    
    def wait_backing_image_manager_restart(self, name, last_creation_time):
        self.backing_image = CRD()
        self.backing_image.wait_backing_image_manager_restart(name, last_creation_time)
    
    def list_backing_image_manager(self):
        self.backing_image = CRD()
        return self.backing_image.list_backing_image_manager()
