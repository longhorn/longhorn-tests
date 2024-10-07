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

    def delete_backing_image_manager(self, name):
        self.backing_image.delete_backing_image_manager(name)
    
    def wait_all_backing_image_managers_running(self):
        self.backing_image.wait_all_backing_image_managers_running()

    def wait_backing_image_manager_restart(self, name, last_creation_time):
        self.backing_image.wait_backing_image_manager_restart(name, last_creation_time)

    def list_backing_image_manager(self):
        return self.backing_image.list_backing_image_manager()

    def delete_all_backing_image_managers_and_wait_for_recreation(self):
        backing_image_managers = self.backing_image.list_backing_image_manager()
        for backing_image in backing_image_managers["items"]:
            name = backing_image["metadata"]["name"]
            last_creation_time = backing_image["metadata"]["creationTimestamp"]
            self.backing_image.delete_backing_image_manager(name)
            self.backing_image.wait_backing_image_manager_restart(name, last_creation_time)
