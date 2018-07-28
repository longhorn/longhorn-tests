#!/usr/sbin/python
import pytest

import common
from common import client, core_api, flexvolume, pod  # NOQA
from common import Gi, DEFAULT_VOLUME_SIZE, VOLUME_RWTEST_SIZE
from common import create_and_wait_pod, delete_and_wait_pod
from common import generate_random_data, read_volume_data
from common import wait_for_volume_detached


@pytest.mark.coretest   # NOQA
@pytest.mark.flexvolume  # NOQA
def test_flexvolume_mount(client, core_api, flexvolume, pod): # NOQA
    """
    Test that a statically defined volume can be created, mounted, unmounted,
    and deleted properly on the Kubernetes cluster.

    Fixtures are torn down here in reverse order that they are specified as a
    parameter. Take caution when reordering test fixtures.
    """

    pod_name = 'flexvolume-mount-test'
    pod['metadata']['name'] = pod_name
    pod['spec']['containers'][0]['volumeMounts'][0]['name'] = \
        flexvolume['name']
    pod['spec']['volumes'] = [
        flexvolume
    ]
    volume_size = DEFAULT_VOLUME_SIZE * Gi

    create_and_wait_pod(core_api, pod)

    volumes = client.list_volume()
    assert len(volumes) == 1
    assert volumes[0]["name"] == flexvolume['name']
    assert volumes[0]["size"] == str(volume_size)
    assert volumes[0]["numberOfReplicas"] == int(
        flexvolume["flexVolume"]["options"]["numberOfReplicas"])
    assert volumes[0]["state"] == "attached"


@pytest.mark.flexvolume  # NOQA
def test_flexvolume_io(client, core_api, flexvolume, pod):  # NOQA
    """
    Test that input and output on a statically defined volume works as
    expected.

    Fixtures are torn down here in reverse order that they are specified as a
    parameter. Take caution when reordering test fixtures.
    """

    pod_name = 'flexvolume-io-test'
    pod['metadata']['name'] = pod_name
    pod['spec']['containers'][0]['volumeMounts'][0]['name'] = \
        flexvolume['name']
    pod['spec']['volumes'] = [
        flexvolume
    ]
    test_data = generate_random_data(VOLUME_RWTEST_SIZE)

    create_and_wait_pod(core_api, pod)

    common.write_volume_data(core_api, pod_name, test_data)
    delete_and_wait_pod(core_api, pod_name)
    wait_for_volume_detached(client, flexvolume["name"])

    pod_name = 'volume-driver-io-test-2'
    pod['metadata']['name'] = pod_name
    create_and_wait_pod(core_api, pod)

    resp = read_volume_data(core_api, pod_name)

    assert resp == test_data
