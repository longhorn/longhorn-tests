from backing_image import BackingImage


class backing_image_keywords:

    def __init__(self):
        self.backing_image = BackingImage()

    def create_backing_image(self, name, url, expectedChecksum="", dataEngine="v1", minNumberOfCopies=1, check_creation=True):
        self.backing_image.create(name, url, expectedChecksum, dataEngine, minNumberOfCopies, check_creation)

    def all_disk_file_status_are_ready(self, bi_name):
        self.backing_image.all_disk_file_status_are_ready(bi_name)

    def wait_for_all_disk_file_status_are_ready(self, bi_name):
        self.backing_image.wait_for_all_disk_file_status_are_ready(bi_name)

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

    def check_backing_image_manager_images(self, image_name):
        backing_image_managers = self.backing_image.list_backing_image_manager()
        for backing_image_manager in backing_image_managers["items"]:
            name = backing_image_manager["metadata"]["name"]
            spec_image = backing_image_manager.get("spec", {}).get("image")
            if spec_image != image_name:
                raise AssertionError(
                    f"BackingImageManager '{name}' has image '{spec_image}', "
                    f"but expected '{image_name}'"
                )

    def get_backing_image_data_source_pod_count(self):
        response = self.backing_image.list_backing_image_data_source_pod()
        return len(response)

    def wait_backing_image_data_source_pod_created(self, bi_name):
        create_time = self.backing_image.wait_backing_image_data_source_pod_created(bi_name)
        return create_time

    def wait_all_disk_file_status_are_at_state(self, bi_name, expected_state):
        self.backing_image.wait_all_disk_file_status_are_at_state(bi_name, expected_state)

    def check_disk_file_map_contain_specific_message(self, bi_name, expect_message):
        self.backing_image.check_disk_file_map_contain_specific_message(bi_name, expect_message)

    def get_backing_image_manager_pod_on_node(self, node_name):
        return self.backing_image.get_backing_image_manager_pod_on_node(node_name)
