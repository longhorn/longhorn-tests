import time
import yaml

from kubernetes import client
from kubernetes.client import rest

from node_exec.constant import HOST_ROOTFS

from utility.constant import LABEL_TEST
from utility.constant import LABEL_TEST_VALUE
from utility.utility import logging
from utility.utility import generate_name_random
from utility.utility import get_retry_count_and_interval

from workload.constant import IMAGE_BUSYBOX


def new_pod_manifest(pod_name="", image="", command=[], args=[],
                     claim_name="", node_name="", labels={}):
    if pod_name == "":
        pod_name = generate_name_random()
    logging(f"Creating pod for {command} {args} on {node_name}")
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
            'name': pod_name,
            'namespace': 'default',
            'labels': labels
        },
        'spec': {
            'tolerations': [{
                'key': 'node-role.kubernetes.io/control-plane',
                'effect': 'NoSchedule'
            }, {
                'key': 'node-role.kubernetes.io/etcd',
                'effect': 'NoExecute'
            }],
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
                }, {
                    'name': 'rootfs',
                    'mountPath': HOST_ROOTFS
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
            }, {
                'name': 'rootfs',
                'hostPath': {
                    'path': '/'
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


def new_busybox_manifest(pod_name, claim_name):
    logging(f"Creating busybox pod {pod_name} using pvc {claim_name}")
    filepath = "./templates/workload/pod.yaml"
    with open(filepath, 'r') as f:
        manifest_dict = yaml.safe_load(f)
        manifest_dict['spec']['volumes'][0]['persistentVolumeClaim']['claimName'] = claim_name
        manifest_dict['metadata']['name'] = pod_name
        manifest_dict['metadata']['labels']['app'] = pod_name
        return manifest_dict


def create_pod(manifest, is_wait_for_pod_running=False):
    core_api = client.CoreV1Api()

    name = manifest['metadata']['name']
    namespace = manifest['metadata']['namespace']

    core_api.create_namespaced_pod(body=manifest, namespace=namespace)

    if is_wait_for_pod_running:
        wait_for_pod_status(name, 'Running', namespace=namespace)

    return get_pod(name, namespace=namespace)


def delete_pod(name, namespace='default', wait=True):
    logging(f"Deleting pod {name} in namespace {namespace}")
    core_api = client.CoreV1Api()
    retry_count, retry_interval = get_retry_count_and_interval()
    for i in range(retry_count):
        try:
            core_api.delete_namespaced_pod(name=name, namespace=namespace, grace_period_seconds=0)
            if wait:
                wait_delete_pod(name, namespace)
            break
        except rest.ApiException as e:
            if e.status == 404:
                logging(f"Deleted pod {name} in namespace {namespace}")
                return
            else:
                logging(f"Deleting pod {name} in namespace {namespace} error: {e}")
        except Exception as e:
            logging(f"Deleting pod {name} in namespace {namespace} error: {e}")
        time.sleep(retry_interval)


def list_pods(namespace='default', label_selector=None):
    core_api = client.CoreV1Api()
    return core_api.list_namespaced_pod(
        namespace=namespace,
        label_selector=label_selector
    ).items


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


def cleanup_pods():
    pods = list_pods(
        label_selector=f"{LABEL_TEST}={LABEL_TEST_VALUE}"
    )

    logging(f'Cleaning up {len(pods)} pods')
    for pod in pods:
        delete_pod(pod.metadata.name)


def get_pod(name, namespace='default'):
    try:
        core_api = client.CoreV1Api()
        return core_api.read_namespaced_pod(name=name, namespace=namespace)
    except Exception as e:
        if e.reason == 'Not Found':
            return None
        raise e


def wait_for_pod_status(name, status, namespace='default'):
    retry_count, retry_interval = get_retry_count_and_interval()
    is_running = False
    for i in range(retry_count):
        pod = get_pod(name, namespace)

        try:
            logging(f"Waiting for pod {name} status {status}, current status {pod.status.phase} ({i}) ...")
            if pod.status.phase == status:
                is_running = True
                break
        except Exception as e:
            logging(e)

        time.sleep(retry_interval)

    assert is_running


def get_volume_name_by_pod(name, namespace='default'):
    pod = get_pod(name, namespace)
    claim_name = ""
    for volume in pod.spec.volumes:
        if volume.name == 'pod-data':
            claim_name = volume.persistent_volume_claim.claim_name
            break
    assert claim_name, f"Failed to get claim name for pod {pod.metadata.name}"

    api = client.CoreV1Api()
    claim = api.read_namespaced_persistent_volume_claim(name=claim_name, namespace='default')
    return claim.spec.volume_name


def is_pod_terminated_by_kubelet(pod):
    if not pod.status.conditions:
        return False

    for condition in pod.status.conditions:
        if condition.type == "DisruptionTarget" and \
            condition.reason == "TerminationByKubelet" and \
            condition.status == "True":
            return True
    return False


def check_pod_did_not_restart(pod_name):
    core_api = client.CoreV1Api()
    pod = core_api.read_namespaced_pod(name=pod_name, namespace="default")
    if pod.status.container_statuses[0].restart_count != 0:
        logging(f"Unexpected pod restart: {pod}")
        time.sleep(self.retry_count)
        assert False, f"Unexpected pod restart: {pod}"
