import time
import yaml

from kubernetes import client
from kubernetes.client.rest import ApiException

from utility.constant import LABEL_TEST
from utility.constant import LABEL_TEST_VALUE
from utility.constant import BLOCK_PVC_VOLUME_DEVICE_PATH
from utility.utility import get_retry_count_and_interval
from utility.utility import logging

from persistentvolumeclaim import PersistentVolumeClaim


def create_deployment(name, claim_name, replicaset=1, enable_pvc_io_and_liveness_probe=False, block_volume=False, args=None):
    filepath = f"./templates/workload/deployment.yaml"
    with open(filepath, 'r') as f:
        namespace = 'default'
        manifest_dict = yaml.safe_load(f)

        # correct workload name
        manifest_dict['metadata']['name'] = name
        manifest_dict['metadata']['labels']['app'] = name
        manifest_dict['metadata']['labels'][LABEL_TEST] = LABEL_TEST_VALUE
        manifest_dict['spec']['replicas'] = replicaset
        manifest_dict['spec']['selector']['matchLabels']['app'] = name
        manifest_dict['spec']['template']['metadata']['labels']['app'] = name
        manifest_dict['spec']['template']['metadata']['labels'][LABEL_TEST] = LABEL_TEST_VALUE

        # correct claim name
        manifest_dict['spec']['template']['spec']['volumes'][0]['persistentVolumeClaim']['claimName'] = claim_name

        if block_volume:
            # remove volumeMounts for block volume
            pvc_volume_name = manifest_dict['spec']['template']['spec']['volumes'][0]['name']
            container = manifest_dict['spec']['template']['spec']['containers'][0]
            container.pop('volumeMounts', None)

            # add volumeDevices for block volume
            container['volumeDevices'] = [
                {
                    "devicePath": BLOCK_PVC_VOLUME_DEVICE_PATH,
                    "name": pvc_volume_name
                }
            ]
            container['securityContext'] = {
                "runAsUser": 0
            }
            manifest_dict['spec']['template']['spec']['containers'][0] = container

        if enable_pvc_io_and_liveness_probe:
            container = manifest_dict['spec']['template']['spec']['containers'][0]
            container['command'] = ["/bin/sh", "-c"]
            container['args'] = [
                "set -e; "
                "while true; do "
                "  date >> /data/date.log; "
                "  sync; "
                "  sleep 1; "
                "done"
            ]
            container['livenessProbe'] = {
                "exec": {
                    "command": [
                        "sh",
                        "-c",
                        "ls /data && tail -n1 /data/date.log > /dev/null"
                    ]
                },
                "initialDelaySeconds": 5,
                "periodSeconds": 5,
                "failureThreshold": 3
            }

        if args:
            # Allow custom args to be provided to the container
            # command is already set in the template, so we only need to set args
            manifest_dict['spec']['template']['spec']['containers'][0]['args'] = [args]

        api = client.AppsV1Api()

        deployment = api.create_namespaced_deployment(
            namespace=namespace,
            body=manifest_dict)

        PersistentVolumeClaim().set_label(claim_name, 'app', name)

        deployment_name = deployment.metadata.name
        replicas = deployment.spec.replicas

        wait_for_deployment_replicas_ready(deployment_name, replicas)

def wait_for_deployment_replicas_ready(deployment_name, expected_ready_count, namespace='default'):
    api = client.AppsV1Api()

    retry_count, retry_interval = get_retry_count_and_interval()
    for i in range(retry_count):
        logging(f"Waiting for deployment {deployment_name} replica ready ({i}) ...")

        deployment = api.read_namespaced_deployment(
            name=deployment_name,
            namespace=namespace)
        # deployment is none if deployment is not yet created
        if deployment is not None and \
            deployment.status.ready_replicas == expected_ready_count:
            return
        time.sleep(retry_interval)

    assert False, f"Failed to wait for deployment replicas to be ready. Expected {expected_ready_count} replicas. Got {deployment.status.ready_replicas} replicas"

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

def get_deployment(name, namespace='default'):
    api = client.AppsV1Api()
    return api.read_namespaced_deployment(name=name, namespace=namespace)

def list_deployments(namespace='default', label_selector=None):
    api = client.AppsV1Api()
    return api.list_namespaced_deployment(
        namespace=namespace,
        label_selector=label_selector
    )

def scale_deployment(name, replica_count, namespace='default'):
    logging(f"Scaling deployment {name} to {replica_count}")

    apps_v1_api = client.AppsV1Api()

    scale = client.V1Scale(
        metadata=client.V1ObjectMeta(name=name, namespace=namespace),
        spec=client.V1ScaleSpec(replicas=int(replica_count))
    )
    apps_v1_api.patch_namespaced_deployment_scale(name=name, namespace=namespace, body=scale)

    deployment = get_deployment(name, namespace)
    assert deployment.spec.replicas == int(replica_count)
