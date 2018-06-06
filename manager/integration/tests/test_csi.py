import time
import pytest

from common import clients, csi_pvc_name  # NOQA
from common import wait_for_volume_delete, wait_for_volume_state

from kubernetes import client as k8sclient, config as k8sconfig
from kubernetes.stream import stream
from kubernetes.client import Configuration

Gi = (1 * 1024 * 1024 * 1024)

WAIT_POD_RETRY_COUNTS = 200
WAIT_POD_RETRY_INTERVAL = 1

DEFAULT_SC_NAME = "longhorn-csi-test"


def create_sc_and_pvc(volume, pvc_name):
    pvc_manifest = {
        'apiVersion': 'v1',
        'kind': 'PersistentVolumeClaim',
        'metadata': {
            'name': pvc_name
        },
        'spec': {
            'accessModes': [
                'ReadWriteOnce',
            ],
            'resources': {
                'requests': {
                    'storage': volume['size']
                },
            },
            'storageClassName': 'longhorn-csi'
        }
    }

    sc_manifest = {
        'apiVersion': 'storage.k8s.io/v1',
        'kind': 'StorageClass',
        'metadata': {
            'name': DEFAULT_SC_NAME
        },
        'provisioner': 'longhorn-csi-plugin',
        'parameters': {
            'numberOfReplicas': volume['numberOfReplicas'],
            'staleReplicaTimeout': volume['staleReplicaTimeout']
        },
        'reclaimPolicy': 'Delete'
    }

    core_api = k8sclient.CoreV1Api()
    core_api.create_namespaced_persistent_volume_claim(
        body=pvc_manifest,
        namespace='default')

    storage_api = k8sclient.StorageV1Api()
    storage_api.create_storage_class(
        body=sc_manifest)


def create_pod(api, pod_name, volume, pvc_name):
    pod_manifest = {
        'apiVersion': 'v1',
        'kind': 'Pod',
        'metadata': {
            'name': pod_name
        },
        'spec': {
            'containers': [{
                'image': 'busybox',
                'imagePullPolicy': 'IfNotPresent',
                'name': 'sleep',
                "args": [
                    "/bin/sh",
                    "-c",
                    "while true;do date;sleep 5; done"
                ],
                "volumeMounts": [{
                    "name": "data",
                    "mountPath": "/data"
                }],
            }],
            'volumes': [{
                'name': 'data',
                'persistentVolumeClaim': {
                    'claimName': pvc_name,
                    'readOnly': False
                }
            }]
        }
    }
    api.create_namespaced_pod(
        body=pod_manifest,
        namespace='default')


def get_volume_name(pvc_name):
    core_api = k8sclient.CoreV1Api()
    pvc = core_api.read_namespaced_persistent_volume_claim(
        name=pvc_name, namespace='default')
    return pvc.spec.volume_name


def wait_pod_ready(api, pod_name):
    for i in range(WAIT_POD_RETRY_COUNTS):
        pod = api.read_namespaced_pod(
            name=pod_name,
            namespace='default')
        if pod.status.phase != 'Pending':
            break
        time.sleep(WAIT_POD_RETRY_INTERVAL)
    assert pod.status.phase == 'Running'


def delete_pod(api, pod_name):
    api.delete_namespaced_pod(
        name=pod_name,
        namespace='default', body=k8sclient.V1DeleteOptions())


def delete_pvc_and_sc(pvc_name):
    core_api = k8sclient.CoreV1Api()
    core_api.delete_namespaced_persistent_volume_claim(
        name=pvc_name,
        namespace='default', body=k8sclient.V1DeleteOptions())

    storage_api = k8sclient.StorageV1Api()
    storage_api.delete_storage_class(
        name=DEFAULT_SC_NAME,
        body=k8sclient.V1DeleteOptions())


@pytest.mark.csi  # NOQA
def test_csi_volume_mount(clients, csi_pvc_name): # NOQA
    c = Configuration()
    c.assert_hostname = False
    Configuration.set_default(c)
    k8sconfig.load_incluster_config()
    api = k8sclient.CoreV1Api()

    for _, client in clients.iteritems():
        break
    pod_name = 'volume-csi-mount-test'
    volume_size = 3 * Gi
    volume = {
        'size': str(volume_size >> 30) + 'Gi',
        'numberOfReplicas': '3', 'staleReplicaTimeout': '20'}

    create_sc_and_pvc(volume, csi_pvc_name)
    create_pod(api, pod_name, volume, csi_pvc_name)
    wait_pod_ready(api, pod_name)
    volume_name = get_volume_name(csi_pvc_name)

    volumes = client.list_volume()
    assert len(volumes) == 1
    assert volumes[0]["name"] == volume_name
    assert volumes[0]["size"] == str(volume_size)
    assert volumes[0]["numberOfReplicas"] == int(volume["numberOfReplicas"])
    assert volumes[0]["state"] == "healthy"

    delete_pod(api, pod_name)
    delete_pvc_and_sc(csi_pvc_name)
    wait_for_volume_delete(client, volume_name)


@pytest.mark.csi  # NOQA
def test_csi_volume_io(clients, csi_pvc_name):  # NOQA
    c = Configuration()
    c.assert_hostname = False
    Configuration.set_default(c)
    k8sconfig.load_incluster_config()
    api = k8sclient.CoreV1Api()

    for _, client in clients.iteritems():
        break
    pod_name = 'volume-csi-io-test'
    volume_size = 3 * Gi
    volume = {
        'size': str(volume_size >> 30) + 'Gi',
        'numberOfReplicas': '3', 'staleReplicaTimeout': '20'}

    create_sc_and_pvc(volume, csi_pvc_name)
    create_pod(api, pod_name, volume, csi_pvc_name)
    wait_pod_ready(api, pod_name)

    test_content = "longhorn"
    write_command = [
        '/bin/sh',
        '-c',
        'echo -ne ' + test_content + ' > /data/test; sync']

    stream(
        api.connect_get_namespaced_pod_exec, pod_name, 'default',
        command=write_command,
        stderr=True, stdin=False,
        stdout=True, tty=False)
    delete_pod(api, pod_name)

    wait_for_volume_state(client, get_volume_name(csi_pvc_name), "detached")

    pod_name = 'volume-csi-io-test-2'
    create_pod(api, pod_name, volume, csi_pvc_name)
    wait_pod_ready(api, pod_name)

    read_command = [
        '/bin/sh',
        '-c',
        'cat /data/test']
    resp = stream(
        api.connect_get_namespaced_pod_exec, pod_name, 'default',
        command=read_command,
        stderr=True, stdin=False,
        stdout=True, tty=False)
    assert resp == test_content
    delete_pod(api, pod_name)
    delete_pvc_and_sc(csi_pvc_name)
    wait_for_volume_delete(client, get_volume_name(csi_pvc_name))
