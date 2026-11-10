import time
import yaml

from kubernetes import client
from kubernetes.client.rest import ApiException

from utility.constant import LABEL_TEST
from utility.constant import LABEL_TEST_VALUE
from utility.utility import get_retry_count_and_interval
from utility.utility import logging

from persistentvolumeclaim import PersistentVolumeClaim


def create_daemonset(name, claim_name, args=None, wait=True):
    filepath = f"./templates/workload/daemonset.yaml"
    with open(filepath, 'r') as f:
        namespace = 'default'
        manifest_dict = yaml.safe_load(f)

        manifest_dict['metadata']['name'] = name
        manifest_dict['metadata']['labels']['app'] = name
        manifest_dict['metadata']['labels'][LABEL_TEST] = LABEL_TEST_VALUE
        manifest_dict['spec']['selector']['matchLabels']['app'] = name
        manifest_dict['spec']['template']['metadata']['labels']['app'] = name
        manifest_dict['spec']['template']['metadata']['labels'][LABEL_TEST] = LABEL_TEST_VALUE

        manifest_dict['spec']['template']['spec']['volumes'][0]['persistentVolumeClaim']['claimName'] = claim_name

        if args:
            manifest_dict['spec']['template']['spec']['containers'][0]['args'] = [args]

            if 'apk' in args:
                manifest_dict['spec']['template']['spec']['securityContext'] = {
                    "runAsUser": 0,
                    "runAsGroup": 0,
                    "fsGroup": 0
                }

        api = client.AppsV1Api()

        daemonset = api.create_namespaced_daemon_set(
            namespace=namespace,
            body=manifest_dict)

        PersistentVolumeClaim().set_label(claim_name, 'app', name)

        daemonset_name = daemonset.metadata.name

        if wait:
            wait_for_daemonset_ready(daemonset_name)


def wait_for_daemonset_ready(daemonset_name, namespace='default'):
    api = client.AppsV1Api()

    retry_count, retry_interval = get_retry_count_and_interval()
    for i in range(retry_count):
        logging(f"Waiting for daemonset {daemonset_name} ready ({i}) ...")

        daemonset = api.read_namespaced_daemon_set(
            name=daemonset_name,
            namespace=namespace)
        if daemonset is not None and \
                daemonset.status.desired_number_scheduled > 0 and \
                daemonset.status.number_ready == daemonset.status.desired_number_scheduled:
            return
        time.sleep(retry_interval)

    assert False, f"Failed to wait for daemonset {daemonset_name} to be ready"


def delete_daemonset(name, namespace='default'):
    api = client.AppsV1Api()

    try:
        api.delete_namespaced_daemon_set(
            name=name,
            namespace=namespace,
            grace_period_seconds=0)
    except ApiException as e:
        assert e.status == 404

    retry_count, retry_interval = get_retry_count_and_interval()
    for _ in range(retry_count):
        resp = api.list_namespaced_daemon_set(namespace=namespace)
        deleted = True
        for item in resp.items:
            if item.metadata.name == name:
                deleted = False
                break
        if deleted:
            break
        time.sleep(retry_interval)
    assert deleted


def list_daemonsets(namespace='default', label_selector=None):
    api = client.AppsV1Api()
    return api.list_namespaced_daemon_set(
        namespace=namespace,
        label_selector=label_selector
    )

