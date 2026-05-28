from enginefrontend.base import Base
from enginefrontend.crd import CRD

from strategy import LonghornOperationStrategy

from utility.utility import logging
from utility.utility import get_retry_count_and_interval

import time


class EngineFrontend(Base):

    _strategy = LonghornOperationStrategy.CRD

    def __init__(self):
        self.retry_count, self.retry_interval = get_retry_count_and_interval()
        if self._strategy == LonghornOperationStrategy.CRD:
            self.enginefrontend = CRD()

    def get_enginefrontends(self, volume_name):
        return self.enginefrontend.get_enginefrontends(volume_name)

    def get_enginefrontend(self, volume_name):
        enginefrontends = self.get_enginefrontends(volume_name)
        assert len(enginefrontends) == 1, \
            f"Expected exactly one enginefrontend but found {len(enginefrontends)}"

        return enginefrontends[0]

    def get_enginefrontend_endpoint(self, volume_name):
        for i in range(self.retry_count):
            logging(f"Trying to get enginefrontend endpoint for volume {volume_name} ... ({i})")
            try:
                enginefrontend = self.get_enginefrontend(volume_name)
                endpoint = enginefrontend.get('status', {}).get('endpoint', '')
                if endpoint:
                    logging(f"Got volume {volume_name} enginefrontend endpoint: {endpoint}")
                    return endpoint
                else:
                    logging(f"EngineFrontend endpoint is empty: {enginefrontend.get('status', {})}")
            except Exception as e:
                logging(f"Getting enginefrontend endpoint for volume {volume_name} error: {e}")
            time.sleep(self.retry_interval)
        assert False, f"Failed to get enginefrontend endpoint for volume {volume_name}"

    def get_node(self, volume_name):
        """
        Get the node where the volume's enginefrontend CR is running.
        """
        for i in range(self.retry_count):
            logging(f"Trying to get enginefrontend node for volume {volume_name} ... ({i})")
            try:
                enginefrontend = self.get_enginefrontend(volume_name)
                enginefrontend_node = enginefrontend["spec"]["nodeID"]
                if enginefrontend_node:
                    logging(f"Volume {volume_name} enginefrontend is running on node: {enginefrontend_node}")
                    return enginefrontend_node
                else:
                    raise RuntimeError(f"Unexpected empty enginefrontend nodeID: {enginefrontend['spec']}")
            except Exception as e:
                logging(f"Getting enginefrontend node for volume {volume_name} error: {e}")
            time.sleep(self.retry_interval)
        assert False, f"Failed to get enginefrontend node for volume {volume_name}"
