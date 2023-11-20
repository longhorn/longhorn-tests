import time
import yaml

from kubernetes import client
from kubernetes.client.rest import ApiException

from utility.utility import get_name_suffix
from utility.utility import get_retry_count_and_interval
from utility.utility import logging


def create_statefulset(volume_type, option):
    filepath = "./templates/workload/statefulset.yaml"
    with open(filepath, 'r') as f:
        namespace = 'default'
        manifest_dict = yaml.safe_load(f)
        suffix = get_name_suffix(volume_type, option)
        # correct workload name
        manifest_dict['metadata']['name'] += suffix
        manifest_dict['spec']['selector']['matchLabels']['app'] += suffix
        manifest_dict['spec']['serviceName'] += suffix
        manifest_dict['spec']['template']['metadata']['labels']['app'] += suffix
        # correct storageclass name
        if option:
            manifest_dict['spec']['volumeClaimTemplates'][0]['spec']['storageClassName'] += f"-{option}"
        # correct access mode`
        if volume_type == 'rwx':
            manifest_dict['spec']['volumeClaimTemplates'][0]['spec']['accessModes'][0] = 'ReadWriteMany'
        api = client.AppsV1Api()

        statefulset = api.create_namespaced_stateful_set(
            body=manifest_dict,
            namespace=namespace)

        statefulset_name = statefulset.metadata.name
        replicas = statefulset.spec.replicas

        wait_for_statefulset_replicas_ready(statefulset_name, replicas)

    return statefulset_name


def wait_for_statefulset_replicas_ready(statefulset_name, expected_ready_count, namespace='default'):
    apps_v1_api = client.AppsV1Api()

    retry_count, retry_interval = get_retry_count_and_interval()
    for i in range(retry_count):
        logging(f"Waiting for statefulset {statefulset_name} replica ready ({i}) ...")

        statefulset = apps_v1_api.read_namespaced_stateful_set(
            name=statefulset_name,
            namespace=namespace)
        # statefulset is none if statefulset is not yet created
        if statefulset is not None and \
            statefulset.status.ready_replicas == expected_ready_count:
            break
        time.sleep(retry_interval)

    assert statefulset.status.ready_replicas == expected_ready_count


def delete_statefulset(name, namespace='default'):
    api = client.AppsV1Api()

    try:
        api.delete_namespaced_stateful_set(
            name=name,
            namespace=namespace,
            grace_period_seconds=0)
    except ApiException as e:
        assert e.status == 404

    retry_count, retry_interval = get_retry_count_and_interval()
    for _ in range(retry_count):
        resp = api.list_namespaced_stateful_set(namespace=namespace)
        deleted = True
        for item in resp.items:
            if item.metadata.name == name:
                deleted = False
                break
        if deleted:
            break
        time.sleep(retry_interval)
    assert deleted


def get_statefulset(name, namespace='default'):
    api = client.AppsV1Api()
    return api.read_namespaced_stateful_set(name=name, namespace=namespace)


def scale_statefulset(name, replica_count, namespace='default'):
    logging(f"Scaling statefulset {name} to {replica_count}")

    apps_v1_api = client.AppsV1Api()

    scale = client.V1Scale(
        metadata=client.V1ObjectMeta(name=name, namespace=namespace),
        spec=client.V1ScaleSpec(replicas=int(replica_count))
    )
    apps_v1_api.patch_namespaced_stateful_set_scale(name=name, namespace=namespace, body=scale)

    statefulset = get_statefulset(name, namespace)
    assert statefulset.spec.replicas == int(replica_count)
