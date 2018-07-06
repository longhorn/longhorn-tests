#!/usr/sbin/python
import time

import common
from common import clients, core_api, pvc_name, volume_name  # NOQA
from common import VOLUME_RWTEST_SIZE
from common import generate_random_data
from common import wait_for_volume_delete

from kubernetes import client as k8sclient
from kubernetes.stream import stream

Gi = (1 * 1024 * 1024 * 1024)

DEFAULT_POD_INTERVAL = 1
DEFAULT_POD_TIMEOUT = 180


DEFAULT_STORAGECLASS_NAME = "longhorn-flexvolume"
DEFAULT_VOLUME_SIZE = 3  # In Gi


DEFAULT_STORAGECLASS_SPEC = {
    'numberOfReplicas': '3',
    'staleReplicaTimeout': '30'
}


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


def create_dynamic_volume_spec(name):
    # type: (str) -> dict
    """
    Generate a volume manifest using the given name for the PVC.

    This spec is used to test dynamically provisioned PersistentVolumes (those
    created using a storage class).
    """
    return {
        'name': 'pod-data',
        'persistentVolumeClaim': {
            'claimName': name,
            'readOnly': False
        }
    }


def create_static_volume_spec(name, options):
    # type: (str, dict) -> dict
    """
    Generate a volume manifest using the volume name and various options.

    This spec is used to test statically defined PersistentVolumes (those not
    created using a storage class).
    """
    return {
        'name': name,
        'flexVolume': {
            'driver': 'rancher.io/longhorn',
            'fsType': 'ext4',
            'options': options
        }
    }


def create_storage(storage_class, volume):
    # type: (dict, dict)
    """Create a StorageClass and PersistentVolumeClaim for testing."""
    sc_manifest = {
        'apiVersion': 'storage.k8s.io/v1',
        'kind': 'StorageClass',
        'metadata': {
            'name': DEFAULT_STORAGECLASS_NAME
        },
        'provisioner': 'rancher.io/longhorn',
        'parameters': {
            'numberOfReplicas': storage_class['numberOfReplicas'],
            'staleReplicaTimeout': storage_class['staleReplicaTimeout']
        },
        'reclaimPolicy': 'Delete'
    }
    storage_api = k8sclient.StorageV1Api()
    storage_api.create_storage_class(
        body=sc_manifest)

    pvc_manifest = {
        'apiVersion': 'v1',
        'kind': 'PersistentVolumeClaim',
        'metadata': {
            'name': volume['pvc_name']
        },
        'spec': {
            'accessModes': [
                'ReadWriteOnce'
            ],
            'resources': {
                'requests': {
                    'storage': volume['size']
                }
            },
            'storageClassName': DEFAULT_STORAGECLASS_NAME
        }
    }
    api = k8sclient.CoreV1Api()
    api.create_namespaced_persistent_volume_claim(
        body=pvc_manifest,
        namespace='default')


def delete_and_wait_storage(client, volume, pvc_volume_name):
    """
    Delete the StorageClass and PersistentVolumeClaim following the test.

    This function will block until the volume is deleted or until the operation
    times out, whichever occurs first.
    """
    api = k8sclient.CoreV1Api()
    api.delete_namespaced_persistent_volume_claim(
        name=volume['pvc_name'], namespace='default',
        body=k8sclient.V1DeleteOptions())

    storage_api = k8sclient.StorageV1Api()
    storage_api.delete_storage_class(
        name=DEFAULT_STORAGECLASS_NAME,
        body=k8sclient.V1DeleteOptions())

    wait_for_volume_delete(client, pvc_volume_name)


def get_volume_name(volume):
    # type: (dict) -> str
    """
    Given a PersistentVolumeClaim, return the name of the associated volume.
    """
    api = k8sclient.CoreV1Api()
    pvc = api.read_namespaced_persistent_volume_claim(
        name=volume['pvc_name'], namespace='default')
    return pvc.spec.volume_name


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


def test_dynamic_volume_mount(clients, core_api, pvc_name):  # NOQA
    """
    Test that a StorageClass provisioned volume can be created, mounted,
    unmounted, and deleted properly on the Kubernetes cluster.
    """
    for _, client in clients.iteritems():
        break

    # Prepare pod and volume specs.
    pod_name = 'flexvolume-mount-test'
    volume_size = DEFAULT_VOLUME_SIZE * Gi
    pvc = {
        'pvc_name': pvc_name,
        'size': size_to_string(volume_size)
    }
    volume = create_dynamic_volume_spec(pvc_name)

    create_storage(DEFAULT_STORAGECLASS_SPEC, pvc)
    create_and_wait_pod(core_api, pod_name, volume)
    pvc_volume_name = get_volume_name(pvc)

    # Confirm that the volume has all the correct parameters we gave it.
    volumes = client.list_volume()
    assert len(volumes) == 1
    assert volumes[0]["name"] == pvc_volume_name
    assert volumes[0]["size"] == str(volume_size)
    assert volumes[0]["numberOfReplicas"] == \
        int(DEFAULT_STORAGECLASS_SPEC["numberOfReplicas"])
    assert volumes[0]["state"] == "attached"

    delete_pod(core_api, pod_name)
    delete_and_wait_storage(client, pvc, pvc_volume_name)


def test_dynamic_volume_params(clients, core_api, pvc_name):  # NOQA
    """
    Test that substituting different StorageClass parameters is reflected in
    the resulting PersistentVolumeClaim.
    """
    for _, client in clients.iteritems():
        break

    # Prepare pod and volume specs.
    pod_name = 'flexvolume-params-test'
    volume_size = 2 * Gi
    storage_class = {
        'numberOfReplicas': '2',
        'staleReplicaTimeout': '20'
    }
    pvc = {
        'pvc_name': pvc_name,
        'size': size_to_string(volume_size)
    }
    volume = create_dynamic_volume_spec(pvc_name)

    create_storage(storage_class, pvc)
    create_and_wait_pod(core_api, pod_name, volume)
    pvc_volume_name = get_volume_name(pvc)

    # Confirm that the volume has all the correct parameters we gave it.
    volumes = client.list_volume()
    assert len(volumes) == 1
    assert volumes[0]["name"] == pvc_volume_name
    assert volumes[0]["size"] == str(volume_size)
    assert volumes[0]["numberOfReplicas"] == \
        int(storage_class["numberOfReplicas"])
    assert volumes[0]["state"] == "attached"

    delete_pod(core_api, pod_name)
    delete_and_wait_storage(client, pvc, pvc_volume_name)


def test_dynamic_volume_io(clients, core_api, pvc_name):  # NOQA
    """
    Test that input and output on a StorageClass provisioned
    PersistentVolumeClaim works as expected.
    """
    for _, client in clients.iteritems():
        break

    # Prepare pod and volume specs.
    pod_name = 'flexvolume-io-test'
    volume_size = DEFAULT_VOLUME_SIZE * Gi
    pvc = {
        'pvc_name': pvc_name,
        'size': size_to_string(volume_size)
    }
    volume = create_dynamic_volume_spec(pvc_name)
    test_data = generate_random_data(VOLUME_RWTEST_SIZE)

    create_storage(DEFAULT_STORAGECLASS_SPEC, pvc)
    create_and_wait_pod(core_api, pod_name, volume)
    pvc_volume_name = get_volume_name(pvc)
    write_volume_data(core_api, pod_name, test_data)
    delete_pod(core_api, pod_name)

    common.wait_for_volume_detached(client, pvc_volume_name)

    pod_name = 'flexvolume-provisioner-io-test-2'
    create_and_wait_pod(core_api, pod_name, volume)
    resp = read_volume_data(core_api, pod_name)

    assert resp == test_data
    delete_pod(core_api, pod_name)
    delete_and_wait_storage(client, pvc, pvc_volume_name)


def test_static_volume_mount(clients, core_api, volume_name): # NOQA
    """
    Test that a statically defined volume can be created, mounted, unmounted,
    and deleted properly on the Kubernetes cluster.
    """
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
    volume = create_static_volume_spec(volume_name, options)
    create_and_wait_pod(core_api, pod_name, volume)

    volumes = client.list_volume()
    assert len(volumes) == 1
    assert volumes[0]["name"] == volume["name"]
    assert volumes[0]["size"] == str(volume_size)
    assert volumes[0]["numberOfReplicas"] == int(
        volume["flexVolume"]["options"]["numberOfReplicas"])
    assert volumes[0]["state"] == "attached"

    delete_pod(core_api, pod_name)
    v = common.wait_for_volume_detached(client, volume["name"])
    client.delete(v)
    wait_for_volume_delete(client, volume["name"])


def test_static_volume_io(clients, core_api, volume_name):  # NOQA
    """
    Test that input and output on a statically defined volume works as
    expected.
    """
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
    volume = create_static_volume_spec(volume_name, options)

    create_and_wait_pod(core_api, pod_name, volume)

    test_data = generate_random_data(VOLUME_RWTEST_SIZE)
    write_volume_data(core_api, pod_name, test_data)
    delete_pod(core_api, pod_name)
    common.wait_for_volume_detached(client, volume["name"])

    pod_name = 'volume-driver-io-test-2'
    create_and_wait_pod(core_api, pod_name, volume)

    resp = read_volume_data(core_api, pod_name)

    assert resp == test_data
    delete_pod(core_api, pod_name)
    v = common.wait_for_volume_detached(client, volume["name"])
    client.delete(v)
    wait_for_volume_delete(client, volume["name"])
