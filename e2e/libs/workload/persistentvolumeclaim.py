import time
import yaml

from kubernetes import client
from kubernetes.client.rest import ApiException

from utility.utility import get_name_suffix
from utility.utility import get_retry_count_and_interval


def create_persistentvolumeclaim(volume_type, option):
    filepath = "./templates/workload/pvc.yaml"
    with open(filepath, 'r') as f:
        namespace = 'default'
        manifest_dict = yaml.safe_load(f)
        suffix = get_name_suffix(volume_type, option)
        # correct pvc name
        manifest_dict['metadata']['name'] += suffix
        # correct storageclass name
        if option:
            manifest_dict['spec']['storageClassName'] += f"-{option}"
        # correct access mode`
        if volume_type == 'rwx':
            manifest_dict['spec']['accessModes'][0] = 'ReadWriteMany'
        api = client.CoreV1Api()

        pvc = api.create_namespaced_persistent_volume_claim(
            body=manifest_dict,
            namespace=namespace)

    return pvc.metadata.name


def delete_persistentvolumeclaim(name, namespace='default'):
    api = client.CoreV1Api()
    try:
        api.delete_namespaced_persistent_volume_claim(
            name=name,
            namespace=namespace,
            grace_period_seconds=0)
    except ApiException as e:
        assert e.status == 404

    retry_count, retry_interval = get_retry_count_and_interval()
    for _ in range(retry_count):
        resp = api.list_namespaced_persistent_volume_claim(namespace=namespace)
        deleted = True
        for item in resp.items:
            if item.metadata.name == name:
                deleted = False
                break
        if deleted:
            break
        time.sleep(retry_interval)
    assert deleted
