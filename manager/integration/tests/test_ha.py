import common
import pytest

from common import clients, volume_name  # NOQA
from common import SIZE, DEV_PATH
from common import wait_for_volume_state, wait_for_volume_delete

def test_ha_simple_recovery(clients, volume_name):  # NOQA
    # get a random client
    for host_id, client in clients.iteritems():
        break

    volume = client.create_volume(name=volume_name, size=SIZE,
                                  numberOfReplicas=2)
    volume = wait_for_volume_state(client, volume_name, "detached")
    assert volume["name"] == volume_name
    assert volume["size"] == SIZE
    assert volume["numberOfReplicas"] == 2
    assert volume["state"] == "detached"
    assert volume["created"] != ""

    volume = volume.attach(hostId=host_id)
    volume = wait_for_volume_state(client, volume_name, "healthy")

    volume = client.by_id_volume(volume_name)
    assert volume["endpoint"] == DEV_PATH + volume_name

    assert len(volume["replicas"]) == 2
    replica0 = volume["replicas"][0]
    assert replica0["name"] != ""

    replica1 = volume["replicas"][1]
    assert replica1["name"] != ""

    volume = volume.replicaRemove(name=replica0["name"])
    assert len(volume["replicas"]) == 1
    volume = wait_for_volume_state(client, volume_name, "degraded")

    volume = wait_for_volume_state(client, volume_name, "healthy")

    volume = client.by_id_volume(volume_name)
    assert volume["state"] == "healthy"
    assert len(volume["replicas"]) == 2

    new_replica0 = volume["replicas"][0]
    new_replica1 = volume["replicas"][1]

    assert (replica1["name"] == new_replica0["name"] or
            replica1["name"] == new_replica1["name"])

    volume = volume.detach()
    volume = wait_for_volume_state(client, volume_name, "detached")

    client.delete(volume)
    wait_for_volume_delete(client, volume_name)

    volumes = client.list_volume()
    assert len(volumes) == 0


@pytest.mark.skip(reason="salvage won't work for k8s for now")  # NOQA
def test_ha_salvage(clients, volume_name):  # NOQA
    # get a random client
    for host_id, client in clients.iteritems():
        break

    volume = client.create_volume(name=volume_name, size=SIZE,
                                  numberOfReplicas=2)
    volume = wait_for_volume_state(client, volume_name, "detached")
    assert volume["name"] == volume_name
    assert volume["size"] == SIZE
    assert volume["numberOfReplicas"] == 2
    assert volume["state"] == "detached"
    assert volume["created"] != ""

    volume = volume.attach(hostId=host_id)
    volume = wait_for_volume_state(client, volume_name, "healthy")

    assert len(volume["replicas"]) == 2
    replica0_name = volume["replicas"][0]["name"]
    replica1_name = volume["replicas"][1]["name"]
    common.docker_stop(replica0_name, replica1_name)

    volume = wait_for_volume_state(client, volume_name, "fault")
    assert len(volume["replicas"]) == 2
    assert volume["replicas"][0]["badTimestamp"] != ""
    assert volume["replicas"][1]["badTimestamp"] != ""

    volume.salvage(names=[replica0_name, replica1_name])

    volume = wait_for_volume_state(client, volume_name, "detached")
    assert len(volume["replicas"]) == 2
    assert volume["replicas"][0]["badTimestamp"] == ""
    assert volume["replicas"][1]["badTimestamp"] == ""

    volume = volume.attach(hostId=host_id)
    volume = wait_for_volume_state(client, volume_name, "healthy")

    volume = volume.detach()
    volume = wait_for_volume_state(client, volume_name, "detached")

    client.delete(volume)
    wait_for_volume_delete(client, volume_name)

    volumes = client.list_volume()
    assert len(volumes) == 0
