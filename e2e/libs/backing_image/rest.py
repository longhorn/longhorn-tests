import time

from backing_image.base import Base
from utility.utility import logging
from utility.utility import get_longhorn_client
from utility.utility import get_retry_count_and_interval


class Rest(Base):

    def __init__(self):
        self.retry_count, self.retry_interval = get_retry_count_and_interval()

    def create(self, bi_name, source_type, url, expected_checksum):
        logging(f"Creating backing image {bi_name}")
        get_longhorn_client().create_backing_image(
            name=bi_name,
            sourceType=source_type,
            parameters={
                "url": url
            },
            expectedChecksum=expected_checksum,
            minNumberOfCopies=1
        )

        ready = False
        bi = None
        for i in range(self.retry_count):
            bi = get_longhorn_client().by_id_backing_image(bi_name)
            if len(bi.diskFileStatusMap) > 0 and bi.currentChecksum != "":
                for disk, status in iter(bi.diskFileStatusMap.items()):
                    if status.state == self.BACKING_IMAGE_STATE_READY:
                        ready = True
                        break
            if ready:
                break
            time.sleep(self.retry_interval)

        assert ready, f"expect backing image diskFileStatusMap ready, but it's {bi.diskFileStatusMap}"
        if expected_checksum:
            assert bi.currentChecksum == expected_checksum, f"expect backing image currentChecksum {bi.currentChecksum} equal to expected checksum {expected_checksum}"
        assert bi.sourceType == source_type, f"expect backing image sourceType is {source_type}, but it's {bi.sourceType}"
        assert bi.parameters["url"] == url, f"expect backing image url is {url}, but it's {bi.parameters['url']}"
        assert not bi.deletionTimestamp, f"expect backing image deletionTimestamp is empty, but it's {bi.deletionTimestamp}"

        return bi

    def get(self, bi_name):
        return get_longhorn_client().by_id_backing_image(bi_name)

    def all_disk_file_status_are_ready(self, bi_name):
        bi = self.get(bi_name)
        assert len(bi.diskFileStatusMap) == 3, f"expect backing images on all disks, but it's {bi.diskFileStatusMap}"
        for disk_id, status in bi.diskFileStatusMap.items():
            assert status.state == self.BACKING_IMAGE_STATE_READY, f"expect backing image on disk {disk_id} ready, but it's {status}"

    def clean_up_backing_image_from_a_random_disk(self, bi_name):
        bi = self.get(bi_name)
        disk_ids = list(bi.diskFileStatusMap.keys())
        logging(f"Cleaning up backing image {bi_name} from disk {disk_ids[0]}")
        bi.backingImageCleanup(disks=[disk_ids[0]])

    def delete(self, bi_name):
        logging(f"Deleting backing image {bi_name}")
        get_longhorn_client().delete(self.get(bi_name))

    def wait_for_backing_image_disk_cleanup(self, bi_name, disk_id):
        found = False
        for i in range(self.retry_count):
            logging(f"Waiting for backing image {bi_name} cleaned up from disk {disk_id} ... ({i})")
            found = False
            bi = get_longhorn_client().by_id_backing_image(bi_name)
            for disk, status in bi.diskFileStatusMap.items():
                if disk == disk_id:
                    found = True
                    break
            if not found:
                break
            time.sleep(self.retry_count)
        assert not found

    def wait_for_backing_image_delete(self, bi_name):
        found = False
        for i in range(self.retry_count):
            logging(f"Waiting for backing image {bi_name} deleted ... ({i})")
            bi_list = get_longhorn_client().list_backing_image()
            found = False
            for bi in bi_list:
                if bi.name == bi_name:
                    found = True
                    break
            if not found:
                break
            time.sleep(self.retry_interval)
        assert not found

    def cleanup_backing_images(self):
        backing_images = get_longhorn_client().list_backing_image()
        for bi in backing_images:
            try:
                self.delete(bi.name)
                self.wait_for_backing_image_delete(bi.name)
            except Exception as e:
                logging(f"Cleaning up backing image {bi.name} failed with error {e}")

        for i in range(self.retry_count):
            backing_images = get_longhorn_client().list_backing_image()
            logging(f"Waiting for all backing images {backing_images} cleaned up ... ({i})")
            if len(backing_images) == 0:
                break
            time.sleep(self.retry_interval)
        assert len(get_longhorn_client().list_backing_image()) == 0
    
    def delete_backing_image_manager(self, name):
        return NotImplemented
    
    def wait_all_backing_image_managers_running(self):
        return NotImplemented

    def wait_backing_image_manager_restart(self, name, last_creation_time):
        return NotImplemented

    def list_backing_image_manager(self):
        return NotImplemented
