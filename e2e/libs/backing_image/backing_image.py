from backing_image.base import Base
from backing_image.rest import Rest

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
        return self.backing_image.cleanup_backing_images
