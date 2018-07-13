#!/usr/sbin/python
import pytest

import common
from common import clients, core_api, volume_name  # NOQA
from common import Gi, VOLUME_RWTEST_SIZE
from common import create_and_wait_pod, delete_pod, generate_random_data
from common import read_volume_data, size_to_string, write_volume_data
from common import wait_for_volume_delete


def create_flexvolume_spec(name, options):
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


@pytest.mark.flexvolume  # NOQA
def test_flexvolume_mount(clients, core_api, volume_name): # NOQA
    """
    Test that a statically defined volume can be created, mounted, unmounted,
    and deleted properly on the Kubernetes cluster.
    """
    for _, client in clients.iteritems():
        break
    pod_name = 'flexvolume-mount-test'
    volume_size = 3 * Gi
    options = {
        'size': size_to_string(volume_size),
        'numberOfReplicas': '2',
        'staleReplicaTimeout': '20',
        'fromBackup': ''
    }
    volume = create_flexvolume_spec(volume_name, options)
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


@pytest.mark.flexvolume  # NOQA
def test_flexvolume_io(clients, core_api, volume_name):  # NOQA
    """
    Test that input and output on a statically defined volume works as
    expected.
    """
    for _, client in clients.iteritems():
        break
    pod_name = 'flexvolume-io-test'
    volume_size = 3 * Gi
    options = {
        'size': size_to_string(volume_size),
        'numberOfReplicas': '2',
        'staleReplicaTimeout': '20',
        'fromBackup': ''
    }
    volume = create_flexvolume_spec(volume_name, options)

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
