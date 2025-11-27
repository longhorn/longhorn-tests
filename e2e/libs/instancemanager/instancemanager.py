import time
import json
from kubernetes import client

from node import Node

from utility.utility import get_longhorn_client
from utility.utility import get_retry_count_and_interval
from utility.utility import logging
from utility.utility import subprocess_exec_cmd
import utility.constant as constant
from workload.pod import delete_pod
from workload.pod import list_pods
from datetime import datetime, timezone, timedelta


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

    def wait_for_all_instance_manager_removed(self):
        longhorn_client = get_longhorn_client()

        for i in range(self.retry_count):
            try:
                instance_managers = longhorn_client.list_instance_manager()
                if len(instance_managers) == 0:
                    logging(f"All instance managers have been removed")
                    return
            except Exception as e:
                logging(f"Getting instance manager state error: {e}")

            logging(f"Waiting for all instance managers to be removed, retry ({i}) ... current count: {len(instance_managers)}")
            time.sleep(self.retry_interval)

        assert False, f"Expected all instance managers to be removed, but still found {len(instance_managers)} instance managers: {instance_managers}"

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
                pod = core_api.read_namespaced_pod(name=im_name, namespace=constant.LONGHORN_NAMESPACE)
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
            pod = core_api.read_namespaced_pod(name=im_name, namespace=constant.LONGHORN_NAMESPACE)
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
                ims = list_pods(constant.LONGHORN_NAMESPACE, label_selector)
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
            time.sleep(retry_interval)

        assert False, f"Failed to check instance manager existence"

    def delete_instance_manager_on_node(self, node_name, engine_type="v1"):
        longhorn_client = get_longhorn_client()
        worker_nodes = self.node.list_node_names_by_role("worker")

        try:
            label_selector = f"longhorn.io/component=instance-manager,longhorn.io/data-engine={engine_type},longhorn.io/node={node_name}"
            ims = list_pods(constant.LONGHORN_NAMESPACE, label_selector)
            for im in ims:
                logging(f"Got {engine_type} instance manager running on node {node_name}: {im.metadata.name}")
                delete_pod(im.metadata.name, namespace=constant.LONGHORN_NAMESPACE, wait=False)
                return
        except Exception as e:
            logging(f"Deleting {engine_type} instance manager on node {node_name} error: {e}")

        assert False, f"Failed to delete {engine_type} instance manager on node {node_name}"

    def wait_for_instance_manager_cr_engine_instances_to_be_cleaned_up(self, node_name, engine_type="v1"):
        cmd = f"kubectl get instancemanager -l longhorn.io/node={node_name},longhorn.io/data-engine={engine_type} -n {constant.LONGHORN_NAMESPACE} -ojson"
        for i in range(self.retry_count):
            logging(f"Waiting for engine instances in {engine_type} instance manager on node {node_name} to be cleaned up ... ({i})")
            cr = json.loads(subprocess_exec_cmd(cmd))['items'][0]
            if "instanceEngines" in cr["status"] and cr['status']['instanceEngines']:
                time.sleep(self.retry_interval)
            else:
                return
        assert False, f"Failed to clean up engine instances in {engine_type} instance manager on node {node_name}: {cr}"
