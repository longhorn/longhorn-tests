import time
from kubernetes import client

from node import Node

from utility.utility import get_longhorn_client
from utility.utility import get_retry_count_and_interval
from utility.utility import logging


class InstanceManager:

    def __init__(self):
        self.node = Node()
        self.retry_count, self.retry_interval = get_retry_count_and_interval()

    def wait_for_all_instance_manager_running(self):
        longhorn_client = get_longhorn_client()
        worker_nodes = self.node.list_node_names_by_role("worker")

        for i in range(self.retry_count):
            try:
                instance_managers = longhorn_client.list_instance_manager()
                instance_manager_map = {}
                for im in instance_managers:
                    if im.currentState == "running":
                        instance_manager_map[im.nodeID] = im
                if len(instance_manager_map) == len(worker_nodes):
                    break
            except Exception as e:
                logging(f"Getting instance manager state error: {e}")

            logging(f"Waiting for all instance manager running, retry ({i}) ...")
            time.sleep(self.retry_interval)

        assert len(instance_manager_map) == len(worker_nodes), f"expect all instance managers running, instance_managers = {instance_managers}, instance_manager_map = {instance_manager_map}"

    def check_all_instance_managers_not_restart(self):

        ims = get_longhorn_client().list_instance_manager()
        v1_im_names = [im.name for im in ims if im.dataEngine == "v1"]
        logging(f"Checking v1 instance managers {v1_im_names} didn't restart")

        core_api = client.CoreV1Api()
        for im_name in v1_im_names:
            pod = core_api.read_namespaced_pod(name=im_name, namespace="longhorn-system")
            if pod.status.container_statuses[0].restart_count != 0:
                logging(f"Unexpected instance manager restart: {pod}")
                time.sleep(self.retry_count)
                assert False, f"Unexpected instance manager restart: {pod}"
