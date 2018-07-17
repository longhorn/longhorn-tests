#!/usr/sbin/python
import common

from common import clients, core_api, pod, pvc, storage_class  # NOQA
from common import DEFAULT_VOLUME_SIZE, Gi, VOLUME_RWTEST_SIZE
from common import create_and_wait_pod, create_pvc_spec, delete_and_wait_pod
from common import generate_random_data, get_storage_api_client
from common import read_volume_data, size_to_string, write_volume_data

DEFAULT_POD_INTERVAL = 1
DEFAULT_POD_TIMEOUT = 180

DEFAULT_STORAGECLASS_NAME = "longhorn-provisioner"


def create_storage(api, sc_manifest, pvc_manifest):
    # type: (dict, dict)
    """Create a StorageClass and PersistentVolumeClaim for testing."""
    s_api = get_storage_api_client()
    s_api.create_storage_class(
        body=sc_manifest
    )

    api.create_namespaced_persistent_volume_claim(
        body=pvc_manifest,
        namespace='default')


def get_volume_name(api, pvc_name):
    # type: (dict) -> str
    """
    Given a PersistentVolumeClaim, return the name of the associated volume.
    """
    claim = api.read_namespaced_persistent_volume_claim(
        name=pvc_name, namespace='default')
    return claim.spec.volume_name


def test_provisioner_mount(clients, core_api, storage_class, pvc, pod):  # NOQA
    """
    Test that a StorageClass provisioned volume can be created, mounted,
    unmounted, and deleted properly on the Kubernetes cluster.

    Fixtures are torn down here in reverse order that they are specified as a
    parameter. Take caution when reordering test fixtures.
    """
    for _, client in clients.iteritems():
        break

    # Prepare pod and volume specs.
    pod_name = 'provisioner-mount-test'
    pod['metadata']['name'] = pod_name
    pod['spec']['volumes'] = [
        create_pvc_spec(pvc['metadata']['name'])
    ]
    pvc['spec']['storageClassName'] = DEFAULT_STORAGECLASS_NAME
    storage_class['metadata']['name'] = DEFAULT_STORAGECLASS_NAME
    volume_size = DEFAULT_VOLUME_SIZE * Gi

    create_storage(core_api, storage_class, pvc)
    create_and_wait_pod(core_api, pod)
    pvc_volume_name = get_volume_name(core_api, pvc['metadata']['name'])

    # Confirm that the volume has all the correct parameters we gave it.
    volumes = client.list_volume()
    assert len(volumes) == 1
    assert volumes[0]["name"] == pvc_volume_name
    assert volumes[0]["size"] == str(volume_size)
    assert volumes[0]["numberOfReplicas"] == \
        int(storage_class['parameters']['numberOfReplicas'])
    assert volumes[0]["state"] == "attached"


def test_provisioner_params(clients, core_api, storage_class, pvc, pod):  # NOQA
    """
    Test that substituting different StorageClass parameters is reflected in
    the resulting PersistentVolumeClaim.

    Fixtures are torn down here in reverse order that they are specified as a
    parameter. Take caution when reordering test fixtures.
    """
    for _, client in clients.iteritems():
        break

    # Prepare pod and volume specs.
    pod_name = 'provisioner-params-test'
    volume_size = 2 * Gi
    pod['metadata']['name'] = pod_name
    pod['spec']['volumes'] = [
        create_pvc_spec(pvc['metadata']['name'])
    ]
    pvc['spec']['resources']['requests']['storage'] = \
        size_to_string(volume_size)
    pvc['spec']['storageClassName'] = DEFAULT_STORAGECLASS_NAME
    storage_class['metadata']['name'] = DEFAULT_STORAGECLASS_NAME
    storage_class['parameters'] = {
        'numberOfReplicas': '2',
        'staleReplicaTimeout': '20'
    }

    create_storage(core_api, storage_class, pvc)
    create_and_wait_pod(core_api, pod)
    pvc_volume_name = get_volume_name(core_api, pvc['metadata']['name'])

    # Confirm that the volume has all the correct parameters we gave it.
    volumes = client.list_volume()
    assert len(volumes) == 1
    assert volumes[0]["name"] == pvc_volume_name
    assert volumes[0]["size"] == str(volume_size)
    assert volumes[0]["numberOfReplicas"] == \
        int(storage_class['parameters']['numberOfReplicas'])
    assert volumes[0]["state"] == "attached"


def test_provisioner_io(clients, core_api, storage_class, pvc, pod):  # NOQA
    """
    Test that input and output on a StorageClass provisioned
    PersistentVolumeClaim works as expected.

    Fixtures are torn down here in reverse order that they are specified as a
    parameter. Take caution when reordering test fixtures.
    """
    for _, client in clients.iteritems():
        break

    # Prepare pod and volume specs.
    pod_name = 'provisioner-io-test'
    pod['metadata']['name'] = pod_name
    pod['spec']['volumes'] = [
        create_pvc_spec(pvc['metadata']['name'])
    ]
    pvc['spec']['storageClassName'] = DEFAULT_STORAGECLASS_NAME
    storage_class['metadata']['name'] = DEFAULT_STORAGECLASS_NAME
    test_data = generate_random_data(VOLUME_RWTEST_SIZE)

    create_storage(core_api, storage_class, pvc)
    create_and_wait_pod(core_api, pod)
    pvc_volume_name = get_volume_name(core_api, pvc['metadata']['name'])
    write_volume_data(core_api, pod_name, test_data)
    delete_and_wait_pod(core_api, pod_name)

    common.wait_for_volume_detached(client, pvc_volume_name)

    pod_name = 'flexvolume-provisioner-io-test-2'
    pod['metadata']['name'] = pod_name
    create_and_wait_pod(core_api, pod)
    resp = read_volume_data(core_api, pod_name)

    assert resp == test_data
