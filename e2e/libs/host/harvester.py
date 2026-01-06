import os
import requests
import time
import urllib3

from host.base import Base
from host.constant import NODE_REBOOT_DOWN_TIME_SECOND

from utility.utility import logging
from utility.utility import wait_for_cluster_ready
from utility.utility import get_retry_count_and_interval
from utility.utility import generate_random_id

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


class Harvester(Base):

    def __init__(self):
        super().__init__()
        self.url = f"{os.getenv('LAB_URL')}/k8s/clusters/{os.getenv('LAB_CLUSTER_ID')}/v1/harvester/kubevirt.io.virtualmachines/longhorn-qa"
        self.cookies = {
            'R_SESS': f"{os.getenv('LAB_ACCESS_KEY')}:{os.getenv('LAB_SECRET_KEY')}"
        }
        self.retry_count, self.retry_interval = get_retry_count_and_interval()
        self.snapshot_ids = []

    def reboot_all_nodes(self, shut_down_time_in_sec=NODE_REBOOT_DOWN_TIME_SECOND):
        node_names = [key for key in self.mapping.keys()]

        for node_name in node_names:
            self.power_off_node(node_name)

        logging(f"Wait for {shut_down_time_in_sec} seconds before starting vms")
        time.sleep(shut_down_time_in_sec)

        for node_name in node_names:
            self.power_on_node(node_name)

        wait_for_cluster_ready()

    def reboot_node(self, node_name, shut_down_time_in_sec):
        self.power_off_node(node_name)

        logging(f"Wait for {shut_down_time_in_sec} seconds before starting vms")
        time.sleep(shut_down_time_in_sec)

        self.power_on_node(node_name)

    def reboot_all_worker_nodes(self, shut_down_time_in_sec):
        node_names = self.node.list_node_names_by_role("worker")

        for node_name in node_names:
            self.power_off_node(node_name)

        logging(f"Wait for {shut_down_time_in_sec} seconds before starting vms")
        time.sleep(shut_down_time_in_sec)

        for node_name in node_names:
            self.power_on_node(node_name)

    def power_off_node(self, node_name, waiting=True):
        vm_id = self.mapping[node_name]

        url = f"{self.url}/{vm_id}"
        for i in range(self.retry_count):
            logging(f"Trying to stop vm {vm_id} ... ({i})")
            try:
                resp = requests.post(f"{url}?action=stop", cookies=self.cookies, verify=False)
                logging(f"resp = {resp}")
                assert resp.status_code == 204, f"Failed to stop vm {vm_id} response: {resp.status_code} {resp.reason}, request: {resp.request.url} {resp.request.headers}"
                break
            except Exception as e:
                logging(f"Stopping vm failed with error {e}")
            time.sleep(self.retry_interval)
        logging(f"Stopping vm {vm_id}")

        if not waiting:
            return

        stopped = False
        for i in range(self.retry_count):
            logging(f"Waiting for vm {vm_id} stopped ... ({i})")
            try:
                resp = requests.get(url, cookies=self.cookies, verify=False)
                if "Stopped" in resp.json()['metadata']['fields']:
                    stopped = True
                    break
            except Exception as e:
                logging(f"Getting vm status failed with error {e}")
            time.sleep(self.retry_interval)
        assert stopped, f"Expected vm {vm_id} to be stopped but it's not"

        self.node.wait_for_node_down(vm_id)

    def power_on_node(self, node_name):
        vm_id = self.mapping[node_name]

        url = f"{self.url}/{vm_id}"
        started = False
        for i in range(self.retry_count):
            logging(f"Trying to start vm {vm_id} ... ({i})")
            try:
                resp = requests.post(f"{url}?action=start", cookies=self.cookies, verify=False)
                logging(f"Starting vm {vm_id} response: {resp.status_code} {resp.reason} ... ({i})")
                resp = requests.get(url, cookies=self.cookies, verify=False)
                if "Running" in resp.json()['metadata']['fields']:
                    started = True
                    break
                else:
                    logging(f"Waiting for vm {vm_id} started ... ({i})")
            except Exception as e:
                logging(f"Starting vm failed with error {e}")
            time.sleep(self.retry_interval)

        assert started, f"Expected vm {vm_id} to be started but it's not"
        logging(f"Started vm {vm_id}")

        self.node.wait_for_node_up(vm_id)

    def create_snapshot(self, node_name):

        vm_id = self.mapping[node_name]
        vm_uid = self.get_vm_info(node_name)['metadata']['uid']
        snapshot_name = f"snap-{vm_id}-{generate_random_id(4)}"

        logging(f"Creating vm snapshot {snapshot_name} for {node_name}")

        data = {
	        "metadata": {
		        "name": snapshot_name,
		        "namespace": "longhorn-qa",
		        "ownerReferences": [{
			        "name": vm_id,
			        "kind": "VirtualMachine",
			        "uid": vm_uid,
			        "apiVersion": "kubevirt.io/v1"
		        }]
	        },
	        "spec": {
		        "source": {
			        "apiGroup": "kubevirt.io",
			        "kind": "VirtualMachine",
			        "name": vm_id
		        },
		        "type": "snapshot"
	        },
	        "type": "harvesterhci.io.virtualmachinebackup"
        }

        url = f"{os.getenv('LAB_URL')}/k8s/clusters/{os.getenv('LAB_CLUSTER_ID')}/v1/harvester/harvesterhci.io.virtualmachinebackups/longhorn-qa"

        self.snapshot_ids.append(snapshot_name)

        resp = requests.post(url, cookies=self.cookies, json=data, verify=False)
        logging(f"resp = {resp}")
        assert resp.status_code == 201, f"Failed to create vm snapshot for {node_name} response: {resp.status_code} {resp.reason}, request: {resp.request.url} {resp.request.headers}"
        logging(f"Created vm snapshot {snapshot_name} for {node_name}")

    def cleanup_snapshots(self):
        for snapshot_id in self.snapshot_ids:
            logging(f"Deleting vm snapshot {snapshot_id}")
            url = f"{os.getenv('LAB_URL')}/k8s/clusters/{os.getenv('LAB_CLUSTER_ID')}/v1/harvester/harvesterhci.io.virtualmachinebackups/longhorn-qa/{snapshot_id}"
            resp = requests.delete(url, cookies=self.cookies, verify=False)
            assert resp.status_code == 200, f"Failed to delete vm snapshot {snapshot_id} response: {resp.status_code} {resp.reason}, request: {resp.request.url} {resp.request.headers}"
            logging(f"Deleted vm snapshot {snapshot_id}")

    def get_vm_info(self, node_name):
        vm_id = self.mapping[node_name]

        url = f"{self.url}/{vm_id}"
        for i in range(self.retry_count):
            logging(f"Trying to get vm {vm_id} info ... ({i})")
            try:
                resp = requests.get(url, cookies=self.cookies, verify=False)
                logging(f"resp = {resp}")
                assert resp.status_code == 200, f"Failed to get vm {vm_id} info response: {resp.status_code} {resp.reason}, request: {resp.request.url} {resp.request.headers}"
                return resp.json()
            except Exception as e:
                logging(f"Getting vm info failed with error {e}")
            time.sleep(self.retry_interval)
        assert False, f"Failed to get vm {vm_id} info response: {resp.status_code} {resp.reason}, request: {resp.request.url} {resp.request.headers}"
