import boto3
import logging

from botocore.exceptions import ClientError

class EC2:

    _ec2_instance = boto3.resource('ec2')
    _all_nodes = None

    def __init__(self, all_nodes) -> None:
        super().__init__()
        self._all_nodes = all_nodes

    def get_all_node_instances(self):
        result = []
        for node in self._all_nodes:
            node_name = node['name']
            if node_name == "":
                continue
            instances = self.get_node_instance(node_name)
            result.append(instances)
        return result

    def get_node_instance(self, node_name):
        logging.info(f"getting node {node_name} EC2 instances")

        for node in self._all_nodes:
            if node['name'] == node_name:
                ip_address = node['ip_address']
        assert ip_address != "", f"{node_name}'s ip address is empty"

        filter = [{'Name': 'ip-address', 'Values': [ip_address]}]
        instances = self._ec2_instance.instances.filter(Filters=filter)
        if len(list(instances)) > 0:
            return instances

        filter = [{'Name': 'private-ip-address', 'Values': [ip_address]}]
        instances = self._ec2_instance.instances.filter(Filters=filter)
        return instances

    def power_off_node_instance(self, node_name):
        node_instances = self.get_node_instance(node_name)
        for instance in node_instances:
            try:
                instance.stop()
                instance.wait_until_stopped()
            except ClientError as e:
                logging.error(f"failed to stop node instance: {e}")
        logging.info("finished powering off node instances")

    def power_on_node_instance(self, node_name=""):
        node_instances = []
        if node_name == "":
            logging.info("powering on all cluster node instances")
            node_instances= self.get_all_node_instances()
        else:
            logging.info(f"powering on node instances: {node_name}")
            node_instances.append(self.get_node_instance(node_name))

        for instances in node_instances:
            for instance in instances:
                if instance.state["Name"] != "running":
                    try:
                        instance.start()
                        instance.wait_until_running()
                    except ClientError as e:
                        logging.error(f"failed to start node instance: {e}")
