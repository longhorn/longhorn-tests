from kubernetes import client
from datetime import datetime

from sharemanager.base import Base
from utility.utility import logging
from utility.utility import get_retry_count_and_interval
import utility.constant as constant
import time

class CRD(Base):

    def __init__(self):
        self.obj_api = client.CustomObjectsApi()
        self.retry_count, self.retry_interval = get_retry_count_and_interval()

    def list(self, label_selector=None):
        return self.obj_api.list_namespaced_custom_object(
            group="longhorn.io",
            version="v1beta2",
            namespace=constant.LONGHORN_NAMESPACE,
            plural="sharemanagers",
            label_selector=label_selector
        )

    def get(self, name):
        return self.obj_api.get_namespaced_custom_object(
            group="longhorn.io",
            version="v1beta2",
            namespace=constant.LONGHORN_NAMESPACE,
            plural="sharemanagers",
            name=name
        )

    def delete(self, name):
        logging(f"deleting sharemanager {name} ...")
        return self.obj_api.delete_namespaced_custom_object(
            group="longhorn.io",
            version="v1beta2",
            namespace=constant.LONGHORN_NAMESPACE,
            plural="sharemanagers",
            name=name
        )
    
    def wait_for_running(self, name):
        for i in range(self.retry_count):
            sharemanager = self.get(name)
            current_status = sharemanager["status"]["state"]
            logging(f"wait sharemanager {name} running, current status = {current_status}")
            if current_status == "running":
                return
            time.sleep(self.retry_interval)

        assert False, f"Failed to wait sharemanager {name} in running state"

    def wait_for_restart(self, name, last_creation_time):
        for i in range(self.retry_count):
            time.sleep(self.retry_interval)            
            try:
                sharemanager = self.get(name)                    
            except Exception as e:
                logging(f"Finding sharemanager {name} failed with error {e}")
                continue
            
            creation_time = sharemanager["metadata"]["creationTimestamp"]
            fmt = "%Y-%m-%dT%H:%M:%SZ"
            if datetime.strptime(creation_time, fmt) > datetime.strptime(last_creation_time, fmt):
                return

        assert False, f"Wait share manager {name} restart failed ..."
