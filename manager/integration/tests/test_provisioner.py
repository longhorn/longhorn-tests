#!/usr/sbin/python
import common
from common import clients, core_api, pvc_name, volume_name  # NOQA
from common import DEFAULT_LONGHORN_PARAMS
from common import DEFAULT_VOLUME_SIZE, Gi, VOLUME_RWTEST_SIZE
from common import create_and_wait_pod, create_pvc_spec, delete_pod
from common import generate_random_data, read_volume_data, size_to_string
from common import wait_for_volume_delete, write_volume_data

from kubernetes import client as k8sclient

DEFAULT_POD_INTERVAL = 1
DEFAULT_POD_TIMEOUT = 180

DEFAULT_STORAGECLASS_NAME = "longhorn-provisioner"


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


def test_provisioner_mount(clients, core_api, pvc_name):  # NOQA
    """
    Test that a StorageClass provisioned volume can be created, mounted,
    unmounted, and deleted properly on the Kubernetes cluster.
    """
    for _, client in clients.iteritems():
        break

    # Prepare pod and volume specs.
    pod_name = 'provisioner-mount-test'
    volume_size = DEFAULT_VOLUME_SIZE * Gi
    pvc = {
        'pvc_name': pvc_name,
        'size': size_to_string(volume_size)
    }
    volume = create_pvc_spec(pvc_name)

    create_storage(DEFAULT_LONGHORN_PARAMS, pvc)
    create_and_wait_pod(core_api, pod_name, volume)
    pvc_volume_name = get_volume_name(pvc)

    # Confirm that the volume has all the correct parameters we gave it.
    volumes = client.list_volume()
    assert len(volumes) == 1
    assert volumes[0]["name"] == pvc_volume_name
    assert volumes[0]["size"] == str(volume_size)
    assert volumes[0]["numberOfReplicas"] == \
        int(DEFAULT_LONGHORN_PARAMS["numberOfReplicas"])
    assert volumes[0]["state"] == "attached"

    delete_pod(core_api, pod_name)
    delete_and_wait_storage(client, pvc, pvc_volume_name)


def test_provisioner_params(clients, core_api, pvc_name):  # NOQA
    """
    Test that substituting different StorageClass parameters is reflected in
    the resulting PersistentVolumeClaim.
    """
    for _, client in clients.iteritems():
        break

    # Prepare pod and volume specs.
    pod_name = 'provisioner-params-test'
    volume_size = 2 * Gi
    storage_class = {
        'numberOfReplicas': '2',
        'staleReplicaTimeout': '20'
    }
    pvc = {
        'pvc_name': pvc_name,
        'size': size_to_string(volume_size)
    }
    volume = create_pvc_spec(pvc_name)

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


def test_provisioner_io(clients, core_api, pvc_name):  # NOQA
    """
    Test that input and output on a StorageClass provisioned
    PersistentVolumeClaim works as expected.
    """
    for _, client in clients.iteritems():
        break

    # Prepare pod and volume specs.
    pod_name = 'provisioner-io-test'
    volume_size = DEFAULT_VOLUME_SIZE * Gi
    pvc = {
        'pvc_name': pvc_name,
        'size': size_to_string(volume_size)
    }
    volume = create_pvc_spec(pvc_name)
    test_data = generate_random_data(VOLUME_RWTEST_SIZE)

    create_storage(DEFAULT_LONGHORN_PARAMS, pvc)
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
