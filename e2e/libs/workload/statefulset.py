import time
import yaml

from kubernetes import client
from kubernetes.client.rest import ApiException

from utility.constant import LABEL_TEST
from utility.constant import LABEL_TEST_VALUE
from utility.utility import get_retry_count_and_interval
from utility.utility import logging


def create_statefulset(statefulset_name, volume_type, option):
    filepath = "./templates/workload/statefulset.yaml"
    with open(filepath, 'r') as f:
        namespace = 'default'
        manifest_dict = yaml.safe_load(f)

        # correct workload name
        manifest_dict['metadata']['name'] = statefulset_name
        manifest_dict['metadata']['labels'][LABEL_TEST] = LABEL_TEST_VALUE
        manifest_dict['spec']['selector']['matchLabels']['app'] = statefulset_name
        manifest_dict['spec']['serviceName'] = statefulset_name
        manifest_dict['spec']['template']['metadata']['labels']['app'] = statefulset_name

        # correct storageclass name
        if option:
            manifest_dict['spec']['volumeClaimTemplates'][0]['spec']['storageClassName'] += f"-{option}"

        # correct access mode`
        if volume_type == 'RWX':
            manifest_dict['spec']['volumeClaimTemplates'][0]['spec']['accessModes'][0] = 'ReadWriteMany'

        api = client.AppsV1Api()
        statefulset = api.create_namespaced_stateful_set(
            body=manifest_dict,
            namespace=namespace)

        statefulset_name = statefulset.metadata.name
        replicas = statefulset.spec.replicas

        wait_for_statefulset_replicas_ready(statefulset_name, replicas)


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

    #TODO
    # all assertions should be removed
    # because it fails the test case instead keeps the environment
    # it stops us from investigation in the front line
    assert statefulset.status.ready_replicas == expected_ready_count, \
        f"Unexpected statefulset {statefulset_name} ready replicas:\n" \
        f"GOT: {statefulset.status.ready_replicas}\n" \
        f"EXPECT: {expected_ready_count}"


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



def list_statefulsets(namespace='default', label_selector=None):
    api = client.AppsV1Api()
    return api.list_namespaced_stateful_set(
        namespace=namespace,
        label_selector=label_selector
    )


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


def add_or_update_statefulset_annotation(name, annotation_key, annotation_value, namespace="default"):
    statefulset = get_statefulset(name, namespace)

    annotations = statefulset.metadata.annotations
    annotations[annotation_key] = annotation_value
    statefulset.metadata.annotations = annotations

    api = client.AppsV1Api()
    api.patch_namespaced_persistent_volume_claim(
        name=name,
        namespace=namespace,
        body=statefulset
    )

def get_statefulset_annotation_value(name, annotation_key, namespace="default"):
    statefulset = get_statefulset(name, namespace)
    return statefulset['metadata']['annotations'].get(annotation_key)
