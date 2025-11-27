from backing_image.base import Base
from backing_image.rest import Rest
from backing_image.crd import CRD

from strategy import LonghornOperationStrategy
from utility.utility import list_namespaced_pod
from utility.utility import get_retry_count_and_interval
import utility.constant as constant
from time import sleep

class BackingImage(Base):

    _strategy = LonghornOperationStrategy.REST

    def __init__(self):
        self.retry_count, self.retry_interval = get_retry_count_and_interval()
        if self._strategy == LonghornOperationStrategy.REST:
            self.backing_image = Rest()

    def create(self, name, url, expectedChecksum, dataEngine, minNumberOfCopies, check_creation):
        sourceType = self.BACKING_IMAGE_SOURCE_TYPE_DOWNLOAD if url else self.BACKING_IMAGE_SOURCE_TYPE_FROM_VOLUME
        return self.backing_image.create(name, sourceType, url, expectedChecksum, dataEngine, minNumberOfCopies, check_creation)

    def get(self, bi_name):
        return self.backing_image.get(bi_name)

    def all_disk_file_status_are_ready(self, bi_name):
        return self.backing_image.all_disk_file_status_are_ready(bi_name)

    def wait_for_all_disk_file_status_are_ready(self, bi_name):
        return self.backing_image.wait_for_all_disk_file_status_are_ready(bi_name)

    def disk_file_status_match_expected(self, bi_name, expected_ready_count, expected_unknown_count):
        return self.backing_image.disk_file_status_match_expected(bi_name, expected_ready_count, expected_unknown_count)

    def wait_for_disk_file_status_match_expected(self, bi_name, expected_ready_count, expected_unknown_count):
        return self.backing_image.wait_for_disk_file_status_match_expected(bi_name, expected_ready_count, expected_unknown_count)

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
            namespace=constant.LONGHORN_NAMESPACE,
            label_selector=label_selector
        )

    def wait_all_disk_file_status_are_at_state(self, bi_name, expected_state):
        return self.backing_image.wait_all_disk_file_status_are_at_state(bi_name, expected_state)

    def get_backing_image_data_source_pod(self, bi_name):
        label_selector = f'longhorn.io/backing-image-data-source={bi_name}'
        return list_namespaced_pod(
            namespace=constant.LONGHORN_NAMESPACE,
            label_selector=label_selector
        )

    def wait_backing_image_data_source_pod_created(self, bi_name):
        for i in range(self.retry_count):
            data_source_pod = self.get_backing_image_data_source_pod(bi_name)
            if len(data_source_pod) == 1:
                return data_source_pod[0].metadata.creation_timestamp
            sleep(self.retry_interval)
        assert False, f"no data spice pod of {bi_name} created"

    def check_disk_file_map_contain_specific_message(self, bi_name, expected_message):
        return self.backing_image.check_disk_file_map_contain_specific_message(bi_name, expected_message)

    def get_backing_image_manager_pod_on_node(self, node_name):
        pods = list_namespaced_pod(
            namespace=constant.LONGHORN_NAMESPACE,
            label_selector=f"longhorn.io/component=backing-image-manager,longhorn.io/node={node_name}"
        )
        return pods[0].metadata.name

    def wait_for_no_backing_image_data_source_pod_exist(self):
        for i in range(self.retry_count):
            response = self.list_backing_image_data_source_pod()
            if len(response) == 0:
                return
        assert False, f"{len(response)} backing image data source pod exist"
