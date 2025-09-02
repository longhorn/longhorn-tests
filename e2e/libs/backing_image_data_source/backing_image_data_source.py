import time
import json

from utility.utility import logging
from utility.utility import get_retry_count_and_interval
from utility.utility import subprocess_exec_cmd

class BackingImageDataSource:

    BACKING_IMAGE_DOWNLOAD_TIMEOUT = 30

    def __init__(self):
        self.retry_count, self.retry_interval = get_retry_count_and_interval()

    def wait_for_created(self, backing_image_data_source_name):
        cmd = f"kubectl get backingimagedatasources {backing_image_data_source_name} -n longhorn-system -ojson"
        for i in range(self.retry_count):
            logging(f"Waiting for backing image data source {backing_image_data_source_name} created ... ({i})")
            try:
                return json.loads(subprocess_exec_cmd(cmd, verbose=False))
            except Exception as e:
                logging(f"Waiting for backing image data source {backing_image_data_source_name} created: {e}")
            time.sleep(self.retry_interval)
        assert False, f"Failed to wait for backing image data source {backing_image_data_source_name} created"

    def get_by_name(self, backing_image_data_source_name):
        cmd = f"kubectl get backingimagedatasources {backing_image_data_source_name} -n longhorn-system -ojson"
        try:
            return json.loads(subprocess_exec_cmd(cmd, verbose=False))
        except Exception as e:
            logging(f"Failed to get backing image data source {backing_image_data_source_name}: {e}")
            return None

    def get_node_id(self, backing_image_data_source_name):
        data_source = self.get_by_name(backing_image_data_source_name)
        logging(f"Got backing image data source = {data_source}")
        return data_source['spec']['nodeID']

    def get_current_state(self, backing_image_data_source_name):
        return self.get_by_name(backing_image_data_source_name)['status']['currentState']

    def wait_for_state(self, backing_image_data_source_name, state):
        for i in range(self.retry_count):
            current_state = self.get_current_state(backing_image_data_source_name)
            logging(f"Waiting for backing image data source {backing_image_data_source_name} state {state}, currently it's {current_state} ... ({i})")
            if state == current_state:
                return
            time.sleep(self.retry_interval)
        assert False, f"Failed to wait for backing image data source {backing_image_data_source_name} state {state}"

    def should_not_be_in_state(self, backing_image_data_source_name, state):
        for i in range(self.BACKING_IMAGE_DOWNLOAD_TIMEOUT):
            current_state = self.get_current_state(backing_image_data_source_name)
            logging(f"Backing image data source {backing_image_data_source_name} state shouldn't be {state}, currently it's {current_state} ... ({i})")
            if state == current_state:
                assert False, f"Backing image data source {backing_image_data_source_name} state shouldn't be {state}, currently it's {current_state}"
            time.sleep(self.retry_interval)
