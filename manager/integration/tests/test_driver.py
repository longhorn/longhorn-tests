#!/usr/sbin/python
import time

from common import clients, core_api, volume_name  # NOQA
from common import VOLUME_RWTEST_SIZE
from common import generate_random_data
from common import wait_for_volume_delete, wait_for_volume_state

from kubernetes import client as k8sclient
from kubernetes.stream import stream

Gi = (1 * 1024 * 1024 * 1024)

DEFAULT_POD_INTERVAL = 1
DEFAULT_POD_TIMEOUT = 180


def create_and_wait_pod(api, pod_name, volume):
    """
    Creates a new Pod attached to a PersistentVolumeClaim for testing.

    The function will block until the Pod is online or until it times out,
    whichever occurs first. The volume created by the manifest passed in will
    be mounted to '/data'.

    Args:
        api: An instance of CoreV1API.
        pod_name: The name of the Pod.
        volume: The volume manifest.
    """
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
                    'name': volume['name'],
                    'mountPath': '/data'
                }],
            }],
            'volumes': [volume]
        }
    }
    api.create_namespaced_pod(
        body=pod_manifest,
        namespace='default')
    for i in range(DEFAULT_POD_TIMEOUT):
        pod = api.read_namespaced_pod(
            name=pod_name,
            namespace='default')
        if pod.status.phase != 'Pending':
            break
        time.sleep(DEFAULT_POD_INTERVAL)
    assert pod.status.phase == 'Running'


def create_volume_spec(name, options):
    # type: (str, dict)
    """Generate a volume manifest using the volume name and various options."""
    return {
        'name': name,
        'flexVolume': {
            'driver': 'rancher.io/longhorn',
            'fsType': 'ext4',
            'options': options
        }
    }


def delete_pod(api, pod_name):
    """
    Delete a specified Pod from the "default" namespace.

    This function does not check if the Pod does exist and will throw an error
    if a nonexistent Pod is specified.

    Args:
        api: An instance of CoreV1API.
        pod_name: The name of the Pod.
    """
    api.delete_namespaced_pod(
        name=pod_name,
        namespace='default',
        body=k8sclient.V1DeleteOptions())


def read_volume_data(api, pod_name):
    """
    Retrieve data from a Pod's volume.

    Args:
        api: An instance of CoreV1API.
        pod_name: The name of the Pod.

    Returns:
        The data contained within the volume.
    """
    read_command = [
        '/bin/sh',
        '-c',
        'cat /data/test'
    ]
    return stream(
        api.connect_get_namespaced_pod_exec, pod_name, 'default',
        command=read_command, stderr=True, stdin=False, stdout=True,
        tty=False)


def size_to_string(volume_size):
    # type: (int) -> str
    """
    Convert a volume size to string format to pass into Kubernetes.
    Args:
        volume_size: The size of the volume in bytes.
    Returns:
        The size of the volume in gigabytes as a passable string to Kubernetes.
    """
    return str(volume_size >> 30) + 'Gi'


def write_volume_data(api, pod_name, test_data):
    """
    Write data into a Pod's volume.

    Args:
        api: An instance of CoreV1API.
        pod_name: The name of the Pod.
        test_data: The data to be written.
    """
    write_command = [
        '/bin/sh',
        '-c',
        'echo -ne ' + test_data + ' > /data/test; sync'
    ]
    stream(
        api.connect_get_namespaced_pod_exec, pod_name, 'default',
        command=write_command, stderr=True, stdin=False, stdout=True,
        tty=False)


def test_volume_mount(clients, core_api, volume_name): # NOQA
    for _, client in clients.iteritems():
        break
    pod_name = 'volume-driver-mount-test'
    volume_size = 3 * Gi
    options = {
        'size': size_to_string(volume_size),
        'numberOfReplicas': '2',
        'staleReplicaTimeout': '20',
        'fromBackup': ''
    }
    volume = create_volume_spec(volume_name, options)
    create_and_wait_pod(core_api, pod_name, volume)

    volumes = client.list_volume()
    assert len(volumes) == 1
    assert volumes[0]["name"] == volume["name"]
    assert volumes[0]["size"] == str(volume_size)
    assert volumes[0]["numberOfReplicas"] == int(
        volume["flexVolume"]["options"]["numberOfReplicas"])
    assert volumes[0]["state"] == "healthy"

    delete_pod(core_api, pod_name)
    v = wait_for_volume_state(client, volume["name"], "detached")
    client.delete(v)
    wait_for_volume_delete(client, volume["name"])


def test_volume_io(clients, core_api, volume_name):  # NOQA
    for _, client in clients.iteritems():
        break
    pod_name = 'volume-driver-io-test'
    volume_size = 3 * Gi
    options = {
        'size': size_to_string(volume_size),
        'numberOfReplicas': '2',
        'staleReplicaTimeout': '20',
        'fromBackup': ''
    }
    volume = create_volume_spec(volume_name, options)

    create_and_wait_pod(core_api, pod_name, volume)

    test_data = generate_random_data(VOLUME_RWTEST_SIZE)
    write_volume_data(core_api, pod_name, test_data)
    delete_pod(core_api, pod_name)
    wait_for_volume_state(client, volume["name"], "detached")

    pod_name = 'volume-driver-io-test-2'
    create_and_wait_pod(core_api, pod_name, volume)

    resp = read_volume_data(core_api, pod_name)

    assert resp == test_data
    delete_pod(core_api, pod_name)
    v = wait_for_volume_state(client, volume["name"], "detached")
    client.delete(v)
    wait_for_volume_delete(client, volume["name"])
