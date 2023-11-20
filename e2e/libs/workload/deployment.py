import time
import yaml

from kubernetes import client
from kubernetes.client.rest import ApiException

from utility.utility import get_name_suffix
from utility.utility import get_retry_count_and_interval


def create_deployment(volume_type, option):
    filepath = f"./templates/workload/deployment.yaml"
    with open(filepath, 'r') as f:
        namespace = 'default'
        manifest_dict = yaml.safe_load(f)
        suffix = get_name_suffix(volume_type, option)
        # correct workload name
        manifest_dict['metadata']['name'] += suffix
        manifest_dict['metadata']['labels']['app'] += suffix
        manifest_dict['spec']['selector']['matchLabels']['app'] += suffix
        manifest_dict['spec']['template']['metadata']['labels']['app'] += suffix
        # correct claim name
        manifest_dict['spec']['template']['spec']['volumes'][0]['persistentVolumeClaim']['claimName'] += suffix
        api = client.AppsV1Api()

        deployment = api.create_namespaced_deployment(
            namespace=namespace,
            body=manifest_dict)

        deployment_name = deployment.metadata.name
        replicas = deployment.spec.replicas

        retry_count, retry_interval = get_retry_count_and_interval()
        for _ in range(retry_count):
            deployment = api.read_namespaced_deployment(
                name=deployment_name,
                namespace=namespace)
            # deployment is none if deployment is not yet created
            if deployment is not None and \
                deployment.status.ready_replicas == replicas:
                break
            time.sleep(retry_interval)

        assert deployment.status.ready_replicas == replicas

    return deployment_name


def delete_deployment(name, namespace='default'):
    api = client.AppsV1Api()

    try:
        api.delete_namespaced_deployment(
            name=name,
            namespace=namespace,
            grace_period_seconds=0)
    except ApiException as e:
        assert e.status == 404

    retry_count, retry_interval = get_retry_count_and_interval()
    for _ in range(retry_count):
        resp = api.list_namespaced_deployment(namespace=namespace)
        deleted = True
        for item in resp.items:
            if item.metadata.name == name:
                deleted = False
                break
        if deleted:
            break
        time.sleep(retry_interval)
    assert deleted
