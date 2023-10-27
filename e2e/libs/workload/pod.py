import time

from kubernetes import client

from utility.utility import logging
from utility.utility import generate_name
from utility.utility import get_retry_count_and_interval


IMAGE_BUSYBOX = 'busybox:1.34.0'
IMAGE_LITMUX = 'litmuschaos/go-runner:latest'
IMAGE_UBUNTU = 'ubuntu:16.04'

def new_pod_manifest(image="", command=[], args=[],
                     claim_name="", node_name="", labels={}):
    # Set default image and args
    if image is None:
        image = IMAGE_BUSYBOX
        args = [
            '/bin/sh', '-c',
            'while true; do date; sleep 5; done'
        ]

    manifest = {
        'apiVersion': 'v1',
        'kind': 'Pod',
        'metadata': {
            'name': generate_name(),
            'namespace': 'default',
            'labels': labels
        },
        'spec': {
            'nodeName': node_name,
            'restartPolicy': 'Never',
            'containers': [{
                'image': image,
                'imagePullPolicy': 'IfNotPresent',
                'securityContext': {
                    'privileged': True
                },
                'name': 'run',
                'command': command,
                'args': args,
                'volumeMounts': [{
                    'name': 'bus',
                    'mountPath': '/var/run'
                }, {
                    'name': 'rancher',
                    'mountPath': '/var/lib/rancher'
                }]
            }],
            'volumes': [{
                'name': 'bus',
                'hostPath': {
                    'path': '/var/run'
                }
            }, {
                'name': 'rancher',
                'hostPath': {
                    'path': '/var/lib/rancher'
                }
            }]
        }
    }

    if claim_name != "":
        manifest['spec']['volumes'].append({
            'name': 'pod-data',
            'persistentVolumeClaim': {
                'claimName': claim_name
            }
        })

        manifest['spec']['containers'][0]['volumeMounts'].append({
            'name': 'pod-data',
            'mountPath': '/data'
        })

    return manifest

def create_pod(manifest, is_wait_for_pod_running=False):
    core_api = client.CoreV1Api()

    name = manifest['metadata']['name']
    namespace = manifest['metadata']['namespace']

    core_api.create_namespaced_pod(body=manifest, namespace=namespace)

    if is_wait_for_pod_running:
        wait_for_pod_status(name, 'Running', namespace=namespace)

    return get_pod(name, namespace=namespace)

def delete_pod(name, namespace='default'):
    core_api = client.CoreV1Api()
    try:
        core_api.delete_namespaced_pod(name=name, namespace=namespace)
        wait_delete_pod(name)
    except ApiException as e:
        assert e.status == 404

def wait_delete_pod(name, namespace='default'):
    api = client.CoreV1Api()
    retry_count, retry_interval = get_retry_count_and_interval()
    for i in range(retry_count):
        ret = api.list_namespaced_pod(namespace=namespace)
        found = False
        for item in ret.items:
            if item.metadata.name == name:
                found = True
                break
        if not found:
            break
        time.sleep(retry_interval)
    assert not found

def get_pod(name, namespace='default'):
    core_api = client.CoreV1Api()
    return core_api.read_namespaced_pod(name=name, namespace=namespace)

def wait_for_pod_status(name, status, namespace='default'):
    retry_count, retry_interval = get_retry_count_and_interval()
    is_running = False
    for i in range(retry_count):
        pod = get_pod(name, namespace)

        logging(f"Waiting for pod {name} status {status}, current status {pod.status.phase} ({i}) ...")

        if pod.status.phase == status:
            is_running = True
            break

        time.sleep(retry_interval)

    assert is_running
