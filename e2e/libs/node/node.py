from kubernetes import client
import yaml
import time
import logging
from utility.utility import apply_cr_from_yaml, get_cr
from utility.utility import wait_for_cluster_ready
import boto3

RETRY_COUNT = 180
RETRY_INTERVAL = 1

class Node:

    def __init__(self):
        with open('/tmp/instance_mapping', 'r') as f:
            self.mapping = yaml.safe_load(f)
        self.aws_client = boto3.client('ec2')
        #logging.warn(f"describe_instances = {self.aws_client.describe_instances()}")

    def restart_all_nodes(self):
        instance_ids = [value for value in self.mapping.values()]
        print(instance_ids)
        resp = self.aws_client.stop_instances(InstanceIds=instance_ids)
        print(resp)
        waiter = self.aws_client.get_waiter('instance_stopped')
        waiter.wait(InstanceIds=instance_ids)
        print(f"all instances stopped")
        time.sleep(60)
        resp = self.aws_client.start_instances(InstanceIds=instance_ids)
        print(resp)
        waiter = self.aws_client.get_waiter('instance_running')
        waiter.wait(InstanceIds=instance_ids)
        wait_for_cluster_ready()
        print(f"all instances running")

    def reboot_node(self, running_on_node_name, reboot_node_name, shut_down_time_in_sec=10):
        with open('/tmp/instance_mapping', 'r') as f:
            mapping = yaml.safe_load(f)
            reboot_node_id = mapping[reboot_node_name]

        filepath = './templates/litmus/reboot-node.yaml'
        with open(filepath, 'r') as f:
            data = yaml.safe_load(f)
            data['spec']['components']['runner']['nodeSelector']['kubernetes.io/hostname'] = running_on_node_name
            data['spec']['experiments'][0]['spec']['components']['nodeSelector']['kubernetes.io/hostname'] = running_on_node_name
            data['spec']['experiments'][0]['spec']['components']['env'][1]['value'] = str(shut_down_time_in_sec)
            data['spec']['experiments'][0]['spec']['components']['env'][2]['value'] = reboot_node_id

        with open(filepath, 'w') as file:
            yaml.dump(data,file,sort_keys=False)

        apply_cr_from_yaml(filepath)
        time.sleep(shut_down_time_in_sec)

        for i in range(RETRY_COUNT):
            results = get_cr('litmuschaos.io',
                             'v1alpha1',
                             'default',
                             'chaosresults',
                             'reboot-node-ec2-terminate-by-id')
            if results['status']['experimentStatus']['verdict'] == 'Pass':
                break
            time.sleep(RETRY_INTERVAL)
        api = client.CoreV1Api()
        chaosresults_pods = api.list_namespaced_pod(namespace='default', label_selector='name=ec2-terminate-by-id')
        logs = api.read_namespaced_pod_log(name=chaosresults_pods.items[0].metadata.name, namespace='default')
        logging.info(logs)
        assert results['status']['experimentStatus']['verdict'] == 'Pass', \
               f"expect verdict = Pass, but get results = {results}"
