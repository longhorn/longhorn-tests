from backing_image.base import Base
from backing_image.rest import Rest
from backing_image.crd import CRD

from strategy import LonghornOperationStrategy
from utility.utility import list_namespaced_pod

class BackingImage(Base):

    _strategy = LonghornOperationStrategy.REST

    def __init__(self):
        if self._strategy == LonghornOperationStrategy.REST:
            self.backing_image = Rest()

    def create(self, name, url, expectedChecksum, dataEngine, minNumberOfCopies):
        sourceType = self.BACKING_IMAGE_SOURCE_TYPE_DOWNLOAD if url else self.BACKING_IMAGE_SOURCE_TYPE_FROM_VOLUME
        return self.backing_image.create(name, sourceType, url, expectedChecksum, dataEngine, minNumberOfCopies)

    def get(self, bi_name):
        return self.backing_image.get(bi_name)

    def all_disk_file_status_are_ready(self, bi_name):
        return self.backing_image.all_disk_file_status_are_ready(bi_name)

    def not_all_disk_file_status_are_ready(self, bi_name):
        return self.backing_image.not_all_disk_file_status_are_ready(bi_name)

    def wait_for_all_disk_file_status_are_ready(self, bi_name):
        return self.backing_image.wait_for_all_disk_file_status_are_ready(bi_name)

    def clean_up_backing_image_from_a_random_disk(self, bi_name):
        return self.backing_image.clean_up_backing_image_from_a_random_disk(bi_name)

    def delete(self, bi_name):
        return self.backing_image.delete(bi_name)

    def cleanup_backing_images(self):
        return self.backing_image.cleanup_backing_images()

    def delete_backing_image_manager(self, name):
        return self.backing_image.delete_backing_image_manager(name)

    def wait_all_backing_image_managers_running(self):
        return self.backing_image.wait_all_backing_image_managers_running()

    def wait_backing_image_manager_restart(self, name, last_creation_time):
        self.backing_image.wait_backing_image_manager_restart(name, last_creation_time)

    def list_backing_image_manager(self):
        return self.backing_image.list_backing_image_manager()

    def list_backing_image_data_source_pod(self):
        label_selector = 'longhorn.io/component=backing-image-data-source'
        return list_namespaced_pod(
            namespace="longhorn-system",
            label_selector=label_selector
        )
