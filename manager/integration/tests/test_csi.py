#!/usr/sbin/python
import pytest

import common
from common import clients, core_api, volume_name  # NOQA
from common import DEFAULT_LONGHORN_PARAMS, DEFAULT_VOLUME_SIZE, Gi
from common import VOLUME_RWTEST_SIZE
from common import create_and_wait_pod, create_pvc_spec
from common import delete_and_wait_longhorn, delete_pod
from common import generate_random_data, read_volume_data, size_to_string
from common import write_volume_data

from kubernetes import client as k8sclient


def create_pv_storage(api, client, volume, options):
    """
    Manually create a new PV and PVC for testing.
    """
    client.create_volume(name=volume['pvc_name'], size=volume['size'],
                         numberOfReplicas=int(options['numberOfReplicas']))
    common.wait_for_volume_detached(client, volume['pvc_name'])
    pv_manifest = {
        'apiVersion': 'v1',
        'kind': 'PersistentVolume',
        'metadata': {
            'name': volume['pvc_name']
        },
        'spec': {
            'capacity': {
                'storage': volume['size']
            },
            'volumeMode': 'Filesystem',
            'accessModes': ['ReadWriteOnce'],
            'persistentVolumeReclaimPolicy': 'Delete',
            'csi': {
                'driver': 'io.rancher.longhorn',
                'fsType': 'ext4',
                'volumeAttributes': options,
                'volumeHandle': volume['pvc_name']
            }
        }
    }
    api.create_persistent_volume(pv_manifest)

    pvc_manifest = {
        'apiVersion': 'v1',
        'kind': 'PersistentVolumeClaim',
        'metadata': {
            'name': volume['pvc_name']
        },
        'spec': {
            'accessModes': ['ReadWriteOnce'],
            'resources': {
                'requests': {
                    'storage': volume['size']
                }
            },
            'volumeName': volume['pvc_name']
        }
    }
    api.create_namespaced_persistent_volume_claim(
        body=pvc_manifest,
        namespace='default')


def delete_and_wait_pv(api, client, volume):
    """
    Delete the PV and PVC following the test.

    This function will block until the volume is deleted or until the operation
    times out, whichever occurs first.
    """
    api.delete_namespaced_persistent_volume_claim(
        name=volume['pvc_name'], namespace='default',
        body=k8sclient.V1DeleteOptions())
    api.delete_persistent_volume(name=volume['pvc_name'],
                                 body=k8sclient.V1DeleteOptions())

    delete_and_wait_longhorn(client, volume['pvc_name'])


@pytest.mark.csi  # NOQA
def test_csi_mount(clients, core_api, volume_name): # NOQA
    """
    Test that a statically defined CSI volume can be created, mounted,
    unmounted, and deleted properly on the Kubernetes cluster.
    """
    for _, client in clients.iteritems():
        break
    pod_name = 'csi-mount-test'
    volume_size = DEFAULT_VOLUME_SIZE * Gi
    pvc = {
        'pvc_name': volume_name,
        'size': size_to_string(volume_size)
    }
    volume = create_pvc_spec(volume_name)

    create_pv_storage(core_api, client, pvc, DEFAULT_LONGHORN_PARAMS)
    create_and_wait_pod(core_api, pod_name, volume)

    volumes = client.list_volume()
    assert len(volumes) == 1
    assert volumes[0]["name"] == volume_name
    assert volumes[0]["size"] == str(volume_size)
    assert volumes[0]["numberOfReplicas"] == \
        int(DEFAULT_LONGHORN_PARAMS["numberOfReplicas"])
    assert volumes[0]["state"] == "attached"

    delete_pod(core_api, pod_name)
    delete_and_wait_pv(core_api, client, pvc)


@pytest.mark.csi  # NOQA
def test_csi_io(clients, core_api, volume_name):  # NOQA
    """
    Test that input and output on a statically defined CSI volume works as
    expected.
    """
    for _, client in clients.iteritems():
        break
    pod_name = 'csi-io-test'
    volume_size = DEFAULT_VOLUME_SIZE * Gi
    pvc = {
        'pvc_name': volume_name,
        'size': size_to_string(volume_size)
    }
    volume = create_pvc_spec(volume_name)

    create_pv_storage(core_api, client, pvc, DEFAULT_LONGHORN_PARAMS)
    create_and_wait_pod(core_api, pod_name, volume)

    test_data = generate_random_data(VOLUME_RWTEST_SIZE)
    write_volume_data(core_api, pod_name, test_data)
    delete_pod(core_api, pod_name)
    common.wait_for_volume_detached(client, volume_name)

    pod_name = 'csi-io-test-2'
    create_and_wait_pod(core_api, pod_name, volume)

    resp = read_volume_data(core_api, pod_name)

    assert resp == test_data

    delete_pod(core_api, pod_name)
    delete_and_wait_pv(core_api, client, pvc)
