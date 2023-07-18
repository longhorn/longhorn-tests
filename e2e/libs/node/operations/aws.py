from node.operations.abstract_cloud_provider import AbstractCloudProvider
from node import Nodes
from utility import Utility

import boto3
import logging

class EC2(AbstractCloudProvider):

    _ec2_instance = boto3.resource('ec2')

    def __init__(self) -> None:
        super().__init__()

    def get_all_node_instances(self):
        result = []
        for node in Nodes.all_nodes:
            node_name = node['name']
            if node_name == "":
                continue
            instances = self.get_node_instance(node_name)
            result.append(instances)
        return result

    def get_node_instance(self, node_name):
        logging.info(f"getting node {node_name} EC2 instances")

        for node in Nodes.all_nodes:
            if node['name'] == node_name:
                ip_address = node['ip_address']
        if ip_address == "":
            raise Exception(f"{node_name}'s ip address is empty")

        filter = [{'Name': 'ip-address','Values': [ip_address]}]
        instances = self._ec2_instance.instances.filter(Filters=filter)
        if len(list(instances)) > 0:
            return instances

        filter = [{'Name': 'private-ip-address','Values': [ip_address]}]
        instances = self._ec2_instance.instances.filter(Filters=filter)
        return instances

    def power_off_node_instance(self, node_name):
        node_instances = self.get_node_instance(node_name)
        for instance in node_instances:
            instance.stop()
            logging.debug(f'Stopping EC2 instance:', {node_name})
            instance.wait_until_stopped()
            logging.debug(f'EC2 instance "{node_name}" is stopped')
        logging.info("finished powering off node instances")

    def power_on_node_instance(self, node_name=""):
        if node_name == "":
            logging.info("powering on all cluster node instances")
            all_node_instances = self.get_all_node_instances()
            for instances in all_node_instances:
                for instance in instances:
                    logging.debug(f'node_instances: {instance.id}')
                    if instance.state["Name"] != "running":
                        instance.start()
                        logging.debug(f'Starting EC2 instance:', {node_name})
                        instance.wait_until_running()
                        logging.debug(f'EC2 instance "{node_name}" is running')
        else:
            logging.info(f"powering on node instances: {node_name}")
            instances = self.get_node_instance(node_name)
            for instance in instances:
                logging.debug(f'node_instances: {instance}')
                if instance.state["Name"] != "running":
                    instance.start()
                    logging.debug(f'Starting EC2 instance:', {node_name})
                    instance.wait_until_running()
                    logging.debug(f'EC2 instance "{node_name}" is running')

    def reboot_node_instance(self, node_name):
        node_instances = self.get_node_instance(node_name)
        if len(list(node_instances)) == 0:
            logging.warn(f"cannot find node instance")
            return

        for instance in node_instances:
            instance.reboot()
            logging.debug(f'EC2 instance has beend rebooted:', {node_name})
            instance.wait_until_running()
            logging.debug(f'EC2 instance "{node_name}" is running')
        logging.info("finished rebooting node instances")
