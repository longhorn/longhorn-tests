from kubernetes import client
import time

from enginefrontend.base import Base
from utility.utility import logging
from utility.utility import get_retry_count_and_interval
import utility.constant as constant


class CRD(Base):
    def __init__(self):
        self.obj_api = client.CustomObjectsApi()
        self.retry_count, self.retry_interval = get_retry_count_and_interval()

    def get_enginefrontends(self, volume_name):
        logging(f"Getting enginefrontends of {volume_name}")

        label_selector = []
        if volume_name:
            label_selector.append(f"longhornvolume={volume_name}")

        api_response = self.obj_api.list_namespaced_custom_object(
            group="longhorn.io",
            version="v1beta2",
            namespace=constant.LONGHORN_NAMESPACE,
            plural="enginefrontends",
            label_selector=",".join(label_selector)
        )

        if api_response == "" or api_response is None:
            raise Exception(f"failed to get volume {volume_name} enginefrontend")

        enginefrontends = api_response["items"]
        if len(enginefrontends) == 0:
            logging(f"Cannot get volume {volume_name} enginefrontends")

        return enginefrontends
