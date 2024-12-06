import boto3
import time
from host.constant import NODE_REBOOT_DOWN_TIME_SECOND
from utility.utility import logging
from utility.utility import wait_for_cluster_ready
from host.base import Base

class Aws(Base):

    def __init__(self):
        super().__init__()
        self.aws_client = boto3.client('ec2')

    def reboot_all_nodes(self, shut_down_time_in_sec=NODE_REBOOT_DOWN_TIME_SECOND):
        instance_ids = [value for value in self.mapping.values()]

        resp = self.aws_client.stop_instances(InstanceIds=instance_ids, Force=True)
        assert resp['ResponseMetadata']['HTTPStatusCode'] == 200, f"Failed to stop instances {instance_ids} response: {resp}"
        logging(f"Stopping instances {instance_ids}")
        waiter = self.aws_client.get_waiter('instance_stopped')
        waiter.wait(InstanceIds=instance_ids)

        logging(f"Wait for {shut_down_time_in_sec} seconds before starting instances")
        time.sleep(shut_down_time_in_sec)

        resp = self.aws_client.start_instances(InstanceIds=instance_ids)
        logging(f"Starting instances {instance_ids} response: {resp}")
        waiter = self.aws_client.get_waiter('instance_running')
        waiter.wait(InstanceIds=instance_ids)

        wait_for_cluster_ready()

        logging(f"Started instances")

    def reboot_node(self, reboot_node_name, shut_down_time_in_sec=NODE_REBOOT_DOWN_TIME_SECOND):
        instance_ids = [self.mapping[reboot_node_name]]

        resp = self.aws_client.stop_instances(InstanceIds=instance_ids, Force=True)
        assert resp['ResponseMetadata']['HTTPStatusCode'] == 200, f"Failed to stop instances {instance_ids} response: {resp}"
        logging(f"Stopping instances {instance_ids}")
        waiter = self.aws_client.get_waiter('instance_stopped')
        waiter.wait(InstanceIds=instance_ids)
        logging(f"Stopped instances")

        time.sleep(shut_down_time_in_sec)

        resp = self.aws_client.start_instances(InstanceIds=instance_ids)
        logging(f"Starting instances {instance_ids} response: {resp}")
        waiter = self.aws_client.get_waiter('instance_running')
        waiter.wait(InstanceIds=instance_ids)
        logging(f"Started instances")

    def reboot_all_worker_nodes(self, shut_down_time_in_sec=NODE_REBOOT_DOWN_TIME_SECOND):
        instance_ids = [self.mapping[value] for value in self.node.list_node_names_by_role("worker")]

        resp = self.aws_client.stop_instances(InstanceIds=instance_ids, Force=True)
        assert resp['ResponseMetadata']['HTTPStatusCode'] == 200, f"Failed to stop instances {instance_ids} response: {resp}"
        logging(f"Stopping instances {instance_ids}")
        waiter = self.aws_client.get_waiter('instance_stopped')
        waiter.wait(InstanceIds=instance_ids)
        logging(f"Stopped instances")

        time.sleep(shut_down_time_in_sec)

        resp = self.aws_client.start_instances(InstanceIds=instance_ids)
        logging(f"Starting instances {instance_ids} response: {resp}")
        waiter = self.aws_client.get_waiter('instance_running')
        waiter.wait(InstanceIds=instance_ids)
        logging(f"Started instances")

    def power_off_node(self, power_off_node_name, waiting=True):
        instance_ids = [self.mapping[power_off_node_name]]
        resp = self.aws_client.stop_instances(InstanceIds=instance_ids, Force=True)
        assert resp['ResponseMetadata']['HTTPStatusCode'] == 200, f"Failed to stop instances {instance_ids} response: {resp}"
        logging(f"Stopping instances {instance_ids}")
        if waiting:
            waiter = self.aws_client.get_waiter('instance_stopped')
            waiter.wait(InstanceIds=instance_ids)
            logging(f"Stopped instances")

    def power_on_node(self, power_on_node_name):
        instance_ids = [self.mapping[power_on_node_name]]

        resp = self.aws_client.start_instances(InstanceIds=instance_ids)
        logging(f"Starting instances {instance_ids} response: {resp}")
        waiter = self.aws_client.get_waiter('instance_running')
        waiter.wait(InstanceIds=instance_ids)
        logging(f"Started instances")
