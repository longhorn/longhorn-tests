from kubernetes import client
import yaml
import time
from utility.utility import logging
from utility.utility import apply_cr_from_yaml, get_cr
from utility.utility import wait_for_cluster_ready
from utility.utility import list_nodes
import boto3

RETRY_COUNT = 180
RETRY_INTERVAL = 1

class Node:

    def __init__(self):
        with open('/tmp/instance_mapping', 'r') as f:
            self.mapping = yaml.safe_load(f)
        self.aws_client = boto3.client('ec2')

    def reboot_all_nodes(self, shut_down_time_in_sec=60):
        instance_ids = [value for value in self.mapping.values()]

        resp = self.aws_client.stop_instances(InstanceIds=instance_ids)
        logging(f"Stopping instances {instance_ids} response: {resp}")
        waiter = self.aws_client.get_waiter('instance_stopped')
        waiter.wait(InstanceIds=instance_ids)
        logging(f"Stopped instances")

        time.sleep(shut_down_time_in_sec)

        resp = self.aws_client.start_instances(InstanceIds=instance_ids)
        logging(f"Starting instances {instance_ids} response: {resp}")
        waiter = self.aws_client.get_waiter('instance_running')
        waiter.wait(InstanceIds=instance_ids)
        wait_for_cluster_ready()
        logging(f"Started instances")

    def reboot_node(self, reboot_node_name, shut_down_time_in_sec=60):
        instance_ids = [self.mapping[reboot_node_name]]

        resp = self.aws_client.stop_instances(InstanceIds=instance_ids)
        logging(f"Stopping instances {instance_ids} response: {resp}")
        waiter = self.aws_client.get_waiter('instance_stopped')
        waiter.wait(InstanceIds=instance_ids)
        logging(f"Stopped instances")

        time.sleep(shut_down_time_in_sec)

        resp = self.aws_client.start_instances(InstanceIds=instance_ids)
        logging(f"Starting instances {instance_ids} response: {resp}")
        waiter = self.aws_client.get_waiter('instance_running')
        waiter.wait(InstanceIds=instance_ids)
        logging(f"Started instances")

    def reboot_all_worker_nodes(self, shut_down_time_in_sec=60):
        instance_ids = [self.mapping[value] for value in list_nodes()]

        resp = self.aws_client.stop_instances(InstanceIds=instance_ids)
        logging(f"Stopping instances {instance_ids} response: {resp}")
        waiter = self.aws_client.get_waiter('instance_stopped')
        waiter.wait(InstanceIds=instance_ids)
        logging(f"Stopped instances")

        time.sleep(shut_down_time_in_sec)

        resp = self.aws_client.start_instances(InstanceIds=instance_ids)
        logging(f"Starting instances {instance_ids} response: {resp}")
        waiter = self.aws_client.get_waiter('instance_running')
        waiter.wait(InstanceIds=instance_ids)
        logging(f"Started instances")
