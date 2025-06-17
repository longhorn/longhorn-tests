import time

from node import Node

from utility.utility import get_longhorn_client
from utility.utility import get_retry_count_and_interval
from utility.utility import logging
<<<<<<< HEAD
=======
from workload.pod import delete_pod
from workload.pod import list_pods
from datetime import datetime, timezone, timedelta
>>>>>>> 1ab6132 (test(robot): Automate manual test case Test System Upgrade with New Instance Manager)


class InstanceManager:

    def __init__(self):
        self.node = Node()

    def wait_for_all_instance_manager_running(self):
        longhorn_client = get_longhorn_client()
        worker_nodes = self.node.list_node_names_by_role("worker")

        retry_count, retry_interval = get_retry_count_and_interval()
        for i in range(retry_count):
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
<<<<<<< HEAD
=======
            time.sleep(self.retry_interval)

        assert len(instance_manager_map) == len(worker_nodes), f"expect all instance managers running, instance_managers = {instance_managers}, instance_manager_map = {instance_manager_map}"

    def wait_all_instance_managers_recreated(self):
        retry_count, retry_interval = get_retry_count_and_interval()
        core_api = client.CoreV1Api()
        baseline_time = datetime.now(timezone.utc)- timedelta(seconds=10)

        for i in range(retry_count):
            ims = get_longhorn_client().list_instance_manager()
            v1_im_names = [im.name for im in ims if im.dataEngine == "v1"]
            recreated = []
            logging(f"Checking v1 instance managers {v1_im_names} have recreated")

            for im_name in v1_im_names:
                pod = core_api.read_namespaced_pod(name=im_name, namespace="longhorn-system")
                creation_time = pod.metadata.creation_timestamp
                if creation_time > baseline_time:
                    recreated.append(im_name)
                else:
                    logging(f"Instance manager {im_name} not recreated")

            if len(recreated) == len(v1_im_names):
                logging(f"All instance-manager pods have restarted")
                return
            time.sleep(retry_interval)

        assert False, f"Instance managers never recreated after {retry_count} attempts"

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

    def check_instance_manager_existence_on_node(self, node_name, engine_type="v1", exist=True):
        longhorn_client = get_longhorn_client()
        worker_nodes = self.node.list_node_names_by_role("worker")

        retry_count, retry_interval = get_retry_count_and_interval()
        for i in range(retry_count):
            logging(f"Waiting for {engine_type} instance manager {'running' if exist else 'not running'} on node {node_name} ... ({i})")
            try:
                label_selector = f"longhorn.io/component=instance-manager,longhorn.io/data-engine={engine_type},longhorn.io/node={node_name}"
                ims = list_pods("longhorn-system", label_selector)
                if exist:
                    if len(ims) > 0:
                        logging(f"Got {engine_type} instance manager running on node {node_name}")
                        return
                else:
                    if len(ims) == 0:
                        logging(f"Found no {engine_type} instance manager running on node {node_name}")
                        return
            except Exception as e:
                logging(f"Checking instance manager existence error: {e}")
>>>>>>> 1ab6132 (test(robot): Automate manual test case Test System Upgrade with New Instance Manager)
            time.sleep(retry_interval)

        assert len(instance_manager_map) == len(worker_nodes), f"expect all instance managers running, instance_managers = {instance_managers}, instance_manager_map = {instance_manager_map}"
