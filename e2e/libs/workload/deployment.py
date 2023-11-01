import time
import yaml

from kubernetes import client
from kubernetes.client.rest import ApiException

from utility.constant import LABEL_TEST
from utility.constant import LABEL_TEST_VALUE
from utility.utility import get_retry_count_and_interval


def create_deployment(name, claim_name):
    filepath = f"./templates/workload/deployment.yaml"
    with open(filepath, 'r') as f:
        namespace = 'default'
        manifest_dict = yaml.safe_load(f)

        # correct workload name
        manifest_dict['metadata']['name'] = name
        manifest_dict['metadata']['labels']['app'] = name
        manifest_dict['metadata']['labels'][LABEL_TEST] = LABEL_TEST_VALUE
        manifest_dict['spec']['selector']['matchLabels']['app'] = name
        manifest_dict['spec']['template']['metadata']['labels']['app'] = name
        manifest_dict['spec']['template']['metadata']['labels'][LABEL_TEST] = LABEL_TEST_VALUE

        # correct claim name
        manifest_dict['spec']['template']['spec']['volumes'][0]['persistentVolumeClaim']['claimName'] = claim_name
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


def list_deployments(namespace='default', label_selector=None):
    api = client.AppsV1Api()
    return api.list_namespaced_deployment(
        namespace=namespace,
        label_selector=label_selector
    )
