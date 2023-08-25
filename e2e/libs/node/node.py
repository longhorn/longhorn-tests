from kubernetes import client
import yaml
import time
import logging
from utility.utility import apply_cr_from_yaml, get_cr

RETRY_COUNT = 180
RETRY_INTERVAL = 1

class Node:

    def reboot_node(self, running_on_node_name, reboot_node_name, shut_down_time_in_sec=10):
        with open('/tmp/instance_mapping', 'r') as f:
            mapping = yaml.safe_load(f)
            reboot_node_id = mapping[reboot_node_name]
        filepath = './litmus/reboot-engine.yaml'
        with open(filepath, 'r') as f:
            data = yaml.safe_load(f)
            data['spec']['components']['runner']['nodeSelector']['kubernetes.io/hostname'] = running_on_node_name
            data['spec']['experiments'][0]['spec']['components']['nodeSelector']['kubernetes.io/hostname'] = running_on_node_name
            data['spec']['experiments'][0]['spec']['components']['env'][1]['value'] = str(shut_down_time_in_sec)
            data['spec']['experiments'][0]['spec']['components']['env'][2]['value'] = reboot_node_id
        with open(filepath, 'w') as file:
            yaml.dump(data,file,sort_keys=False)
        apply_cr_from_yaml(filepath)
        # wait for reboot completed, node returns to running state
        time.sleep(shut_down_time_in_sec)
        for i in range(RETRY_COUNT):
            results = get_cr('litmuschaos.io',
                             'v1alpha1',
                             'default',
                             'chaosresults',
                             'reboot-engine-ec2-terminate-by-id')
            if results['status']['experimentStatus']['verdict'] == 'Pass':
                break
            time.sleep(RETRY_INTERVAL)
        api = client.CoreV1Api()
        chaosresults_pods = api.list_namespaced_pod(namespace='default', label_selector='name=ec2-terminate-by-id')
        logs = api.read_namespaced_pod_log(name=chaosresults_pods.items[0].metadata.name, namespace='default')
        logging.info(logs)
        assert results['status']['experimentStatus']['verdict'] == 'Pass', \
               f"expect verdict = Pass, but get results = {results}"