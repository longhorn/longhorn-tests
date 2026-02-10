import time

from backing_image.base import Base
from backing_image.crd import CRD

from utility.utility import logging
from utility.utility import get_longhorn_client
from utility.utility import get_retry_count_and_interval


class Rest(Base):

    def __init__(self):
        self.retry_count, self.retry_interval = get_retry_count_and_interval()

    def create(self, name, sourceType, url, expectedChecksum, dataEngine, minNumberOfCopies, check_creation, parameters):
        logging(f"Creating backing image {name}")

        if parameters is None:
            parameters = {"url": url} if url else {}

        get_longhorn_client().create_backing_image(
            name=name,
            sourceType=sourceType,
            parameters=parameters,
            expectedChecksum=expectedChecksum,
            minNumberOfCopies=minNumberOfCopies,
            dataEngine=dataEngine
        )

        if not check_creation:
            return

        bi = None
        ready_copies = 0
        for i in range(self.retry_count):
            bi = get_longhorn_client().by_id_backing_image(name)
            if len(bi.diskFileStatusMap) > 0 and bi.currentChecksum != "":
                ready_copies = 0
                for disk, status in iter(bi.diskFileStatusMap.items()):
                    if status.state == self.BACKING_IMAGE_STATE_READY:
                        ready_copies += 1
            logging(f"Waiting for backing image {name} has {minNumberOfCopies} copies, currently it's {ready_copies} ... ({i})")
            if ready_copies == minNumberOfCopies:
                break
            time.sleep(self.retry_interval)

        assert ready_copies == minNumberOfCopies, f"expect backing image has {minNumberOfCopies} ready copies, but it's only {ready_copies}: {bi.diskFileStatusMap}"
        if expectedChecksum:
            assert bi.currentChecksum == expectedChecksum, f"expect backing image currentChecksum {bi.currentChecksum} equal to expected checksum {expectedChecksum}"
        assert bi.sourceType == sourceType, f"expect backing image sourceType is {sourceType}, but it's {bi.sourceType}"
        if sourceType == self.BACKING_IMAGE_SOURCE_TYPE_DOWNLOAD:
            assert bi.parameters["url"] == url, f"expect backing image url is {url}, but it's {bi.parameters['url']}"
        if sourceType == self.BACKING_IMAGE_SOURCE_TYPE_FROM_VOLUME:
            assert bi.parameters["volume-name"] == parameters["volume-name"], f"expect backing image volume-name is {parameters['volume-name']}, but it's {bi.parameters['volume-name']}"
            assert bi.parameters["export-type"] == parameters["export-type"], f"expect backing image volume-name is {parameters['export-type']}, but it's {bi.parameters['export-type']}"
        assert not bi.deletionTimestamp, f"expect backing image deletionTimestamp is empty, but it's {bi.deletionTimestamp}"

        return bi

    def get(self, bi_name):
        return get_longhorn_client().by_id_backing_image(bi_name)

    def all_disk_file_status_are_ready(self, bi_name):
        bi = self.get(bi_name)
        assert len(bi.diskFileStatusMap) == 3, f"expect backing images on all disks, but it's {bi.diskFileStatusMap}"
        for disk_id, status in bi.diskFileStatusMap.items():
            assert status.state == self.BACKING_IMAGE_STATE_READY, f"expect backing image on disk {disk_id} ready, but it's {status}"

    def wait_for_all_disk_file_status_are_ready(self, bi_name):
        for i in range(self.retry_count):
            try:
                self.all_disk_file_status_are_ready(bi_name)
                return
            except Exception:
                time.sleep(self.retry_interval)
                continue
        assert False, f"not all backingimages diks are ready"

    def disk_file_status_match_expected(self, bi_name, expected_ready_count, expected_unknown_count):
        """
        Check if backing image disk file status matches expected counts
        """
        expected_ready_count = int(expected_ready_count)
        expected_unknown_count = int(expected_unknown_count)
        expected_total_disks = expected_ready_count + expected_unknown_count

        bi = self.get(bi_name)
        ready_count = 0
        unknown_count = 0
        other_count = 0

        for disk_id, status in bi.diskFileStatusMap.items():
            if status.state == self.BACKING_IMAGE_STATE_READY:
                ready_count += 1
            elif status.state == self.BACKING_IMAGE_STATE_UNKNOWN:
                unknown_count += 1
            else:
                other_count += 1
        actual_total = len(bi.diskFileStatusMap)

        if actual_total != expected_total_disks:
            assert False, f"Total disk count mismatch: expected {expected_total_disks}, got {actual_total}. Details: {bi.diskFileStatusMap}"
        if ready_count != expected_ready_count:
            assert False, f"Ready disk count mismatch: expected {expected_ready_count}, got {ready_count}. Details: {bi.diskFileStatusMap}"
        if unknown_count != expected_unknown_count:
            assert False, f"Unknown disk count mismatch: expected {expected_unknown_count}, got {unknown_count}. Details: {bi.diskFileStatusMap}"
        if other_count > 0:
            assert False, f"Unexpected disk states found: {other_count} disks in non-ready/unknown states. Details: {bi.diskFileStatusMap}"

    def wait_for_disk_file_status_match_expected(self, bi_name, expected_ready_count, expected_unknown_count):
        for i in range(self.retry_count):
            try:
                self.disk_file_status_match_expected(bi_name, expected_ready_count, expected_unknown_count)
                return
            except Exception as e:
                if i == self.retry_count - 1:
                    bi = self.get(bi_name)
                    current_ready = 0
                    current_unknown = 0

                    for status in bi.diskFileStatusMap.values():
                        if status.state == self.BACKING_IMAGE_STATE_READY:
                            current_ready += 1
                        elif status.state == self.BACKING_IMAGE_STATE_UNKNOWN:
                            current_unknown += 1
                    current_other = len(bi.diskFileStatusMap) - current_ready - current_unknown

                    error_msg = f"Backing image {bi_name} status mismatch after {self.retry_count} retries:\n"
                    error_msg += f"  • Expected: {expected_ready_count} ready, {expected_unknown_count} unknown\n"
                    error_msg += f"  • Actual: {current_ready} ready, {current_unknown} unknown, {current_other} other states\n"
                    error_msg += f"  • Disk details:\n"
                    for disk_id, status in bi.diskFileStatusMap.items():
                        error_msg += f"    - {disk_id}: {status.state}\n"

                    assert False, error_msg
                time.sleep(self.retry_interval)

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
        # delegate it to CRD since it doesn't have a REST implementation
        return CRD().delete_backing_image_manager(name)

    def wait_all_backing_image_managers_running(self):
        # delegate it to CRD since it doesn't have a REST implementation
        return CRD().wait_all_backing_image_managers_running()

    def wait_backing_image_manager_restart(self, name, last_creation_time):
        # delegate it to CRD since it doesn't have a REST implementation
        return CRD().wait_backing_image_manager_restart(name, last_creation_time)

    def list_backing_image_manager(self):
        # delegate it to CRD since it doesn't have a REST implementation
        return CRD().list_backing_image_manager()

    def all_disk_file_status_are_at_state(self, bi_name, expected_state):
        bi = self.get(bi_name)
        for disk_id, status in bi.diskFileStatusMap.items():
            logging(f"backingimage {bi_name} current state is {status.state}")
            assert status.state == expected_state, f"expect backing image on disk {disk_id} {expected_state}, but it's {status}"

    def wait_all_disk_file_status_are_at_state(self, bi_name, expected_state):
        for i in range(self.retry_count):
            logging(f"waiting backingimage {bi_name} in state {expected_state}")
            try:
                self.all_disk_file_status_are_at_state(bi_name, expected_state)
                return
            except Exception:
                time.sleep(self.retry_interval)
                continue
        assert False, f"not all backingimages diks are {expected_state}"

    def check_disk_file_map_contain_specific_message(self, bi_name, expected_message):
        bi = self.get(bi_name)
        for disk_id, status in bi.diskFileStatusMap.items():
            msg = status.message
            logging(f"backingimage {bi_name} on disk {disk_id} has message: {msg}")
            assert expected_message in msg, f"'{expected_message}' not in backing image {bi_name} disk {disk_id} message"

    def get_backing_image_disk_uuids(self, bi_name):
        bi = self.get(bi_name)
        uuids = []
        for disk_id, status in bi.diskFileStatusMap.items():
          uuids.append(disk_id)
        logging(f"backing image {bi_name} currently have disks files on: {uuids}")
        return uuids
