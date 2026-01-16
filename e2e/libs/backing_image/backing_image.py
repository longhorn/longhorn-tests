from backing_image.base import Base
from backing_image.rest import Rest
from backing_image.crd import CRD

from strategy import LonghornOperationStrategy
from utility.utility import list_namespaced_pod
from utility.utility import get_retry_count_and_interval
import utility.constant as constant
from utility.utility import logging
from utility.utility import subprocess_exec_cmd
from utility.utility import get_longhorn_base_url
from time import sleep

import os
import subprocess

class BackingImage(Base):

    _strategy = LonghornOperationStrategy.REST

    def __init__(self):
        self.retry_count, self.retry_interval = get_retry_count_and_interval()
        if self._strategy == LonghornOperationStrategy.REST:
            self.backing_image = Rest()

    def create(self, name, url, expectedChecksum, dataEngine, minNumberOfCopies, check_creation, parameters):
        sourceType = self.BACKING_IMAGE_SOURCE_TYPE_DOWNLOAD if url else self.BACKING_IMAGE_SOURCE_TYPE_FROM_VOLUME
        return self.backing_image.create(name, sourceType, url, expectedChecksum, dataEngine, minNumberOfCopies, check_creation, parameters)

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

    def wait_for_backing_image_manager_on_node_unknown(self, node_name):
        for i in range(self.retry_count):
            backing_image_managers = self.backing_image.list_backing_image_manager()
            for bim in backing_image_managers["items"]:
                if bim["metadata"]["labels"]["longhorn.io/node"] == node_name and \
                    bim["status"]["currentState"] == "unknown":
                    return
                continue
            sleep(self.retry_interval)
        assert False, f"Waiting backing image manager no node {node_name} timeout"

    def wait_for_backing_image_manager_on_node_terminated(self, node_name):
        for i in range(self.retry_count):
            backing_image_managers = self.backing_image.list_backing_image_manager()
            bim_found = False
            for bim in backing_image_managers["items"]:
                if bim["metadata"]["labels"]["longhorn.io/node"] == node_name:
                    bim_found = True
                    break
            if not bim_found:
                return
            sleep(self.retry_interval)
        assert False, f"Waiting for backing image manager on node {node_name} to not exist timeout"

    def get_backing_image_disk_uuids(self, bi_name):
        return self.backing_image.get_backing_image_disk_uuids(bi_name)

    def download_backing_image(self, bi_name, is_async):
        longhorn_client_base_url = get_longhorn_base_url()
        cmd = f'curl -fL "{longhorn_client_base_url}/v1/backingimages/{bi_name}/download" | gunzip -c > /tmp/{bi_name}'

        if is_async:
            # using a .done file to check download complete and write sha512sum into this file
            async_cmd = (
                f'sh -c "curl -fL {longhorn_client_base_url}/v1/backingimages/{bi_name}/download | '
                f'gunzip -c > /tmp/{bi_name} && '
                f'sha512sum /tmp/{bi_name} | cut -d\' \' -f1 > /tmp/{bi_name}.done" & echo $!'
            )
            proc = subprocess.Popen(async_cmd, shell=True)
            logging(f"Async download started. PID: {proc.pid}")
            return f"PID:{proc.pid}"
        else:
            subprocess_exec_cmd(cmd)
            cmd = f"sha512sum /tmp/{bi_name} | cut -d' ' -f1"
            res = subprocess_exec_cmd(cmd)
            return res.strip()

    def get_backing_image_checksum(self, bi_name):
        bi = self.backing_image.get(bi_name)
        return bi.currentChecksum

    def wait_for_async_download_complete(self, bi_name):
        done_file = f"/tmp/{bi_name}.done"
        logging(f"Waiting for async download to complete: /tmp/{bi_name}")

        for i in range(self.retry_count):
            if os.path.exists(done_file):
                with open(done_file, "r") as f:
                    checksum = f.read().strip()

                if checksum:
                    logging(f"Async download finished. sha512={checksum}")
                    return checksum

            sleep(self.retry_interval)
        assert False, "Download backing image {bi_name} timeout"
