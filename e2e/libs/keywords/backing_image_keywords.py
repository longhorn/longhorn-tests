from backing_image import BackingImage


class backing_image_keywords:

    def __init__(self):
        self.backing_image = BackingImage()

    def create_backing_image(self, bi_name, url, expected_checksum=""):
        self.backing_image.create(bi_name, url, expected_checksum)

    def all_disk_file_status_are_ready(self, bi_name):
        self.backing_image.all_disk_file_status_are_ready(bi_name)

    def clean_up_backing_image_from_a_random_disk(self, bi_name):
        self.backing_image.clean_up_backing_image_from_a_random_disk(bi_name)

    def delete_backing_image(self, bi_name):
        self.backing_image.delete(bi_name)

    def cleanup_backing_images(self):
        self.backing_image.cleanup_backing_images()
