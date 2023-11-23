import time

from node.utility import list_node_names_by_role

from utility.utility import get_longhorn_client
from utility.utility import get_retry_count_and_interval
from utility.utility import logging

def wait_for_all_instance_manager_running():
    longhorn_client = get_longhorn_client()
    worker_nodes = list_node_names_by_role("worker")

    retry_count, retry_interval = get_retry_count_and_interval()
    for _ in range(retry_count):
        logging(f"Waiting for all instance manager running ({_}) ...")
        try:
            instance_managers = longhorn_client.list_instance_manager()
            instance_manager_map = {}
            for im in instance_managers:
                if im.currentState == "running":
                    instance_manager_map[im.nodeID] = im
            if len(instance_manager_map) == len(worker_nodes):
                break
            time.sleep(retry_interval)
        except Exception as e:
            logging(f"Getting instance manager state error: {e}")
    assert len(instance_manager_map) == len(worker_nodes), f"expect all instance managers running, instance_managers = {instance_managers}, instance_manager_map = {instance_manager_map}"
